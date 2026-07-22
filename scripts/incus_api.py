#!/usr/bin/env python3
"""Minimal Incus REST client over the stdlib, for driving the L3 test host.

This box has no curl and no incus/lxc CLI (Ubuntu Core, no apt, no root), but
it does have python3 with ssl+http.client, which is all the Incus API needs:
TLS with a client certificate. Credentials live in ~/.config/incus/
(client.crt/client.key, generated locally, key is 0600).

The server cert is pinned on first contact (TOFU) into ~/.config/incus/
server.crt and verified against that pin on every later call, so this is not
blanket-insecure despite the endpoint being a self-signed IP host.

Usage as a library:
    from incus_api import Incus
    api = Incus()
    api.get("/1.0")
    api.post("/1.0/instances", {...})

Usage as a CLI (for quick pokes):
    python3 scripts/incus_api.py GET /1.0
    python3 scripts/incus_api.py POST /1.0/certificates '{"trust_token": "..."}'
"""
import http.client
import json
import os
import ssl
import sys
import time
from pathlib import Path
from urllib.parse import quote

CONFIG_DIR = Path.home() / ".config" / "incus"
CLIENT_CRT = CONFIG_DIR / "client.crt"
CLIENT_KEY = CONFIG_DIR / "client.key"
SERVER_CRT = CONFIG_DIR / "server.crt"

HOST = os.environ.get("INCUS_HOST", "192.168.0.1")
PORT = int(os.environ.get("INCUS_PORT", "8443"))


class IncusError(RuntimeError):
    pass


def pin_server_cert(host=HOST, port=PORT):
    """Trust-on-first-use: fetch and store the server cert if not already pinned."""
    if SERVER_CRT.exists():
        return SERVER_CRT
    pem = ssl.get_server_certificate((host, port))
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SERVER_CRT.write_text(pem)
    return SERVER_CRT


class Incus:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        if not CLIENT_CRT.exists() or not CLIENT_KEY.exists():
            raise IncusError(
                f"no client keypair at {CLIENT_CRT} / {CLIENT_KEY} - generate one first"
            )
        pin_server_cert(host, port)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.load_cert_chain(certfile=str(CLIENT_CRT), keyfile=str(CLIENT_KEY))
        ctx.load_verify_locations(cafile=str(SERVER_CRT))
        # Self-signed cert for an IP endpoint: we verify it matches the pinned
        # cert exactly (load_verify_locations above), but its CN/SAN will not
        # match the IP, so hostname checking has to be off for the pin to work.
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_REQUIRED
        self.ctx = ctx

    def request_raw(self, method, path, body=None, timeout=60):
        """Return the response body as text, undecoded. Needed for endpoints
        that serve plain files rather than JSON (e.g. exec output logs)."""
        conn = http.client.HTTPSConnection(
            self.host, self.port, context=self.ctx, timeout=timeout
        )
        try:
            payload = json.dumps(body) if body is not None else None
            headers = {"Content-Type": "application/json"} if payload else {}
            conn.request(method, path, body=payload, headers=headers)
            resp = conn.getresponse()
            return resp.read().decode(errors="replace")
        finally:
            conn.close()

    def request(self, method, path, body=None, timeout=60):
        raw = self.request_raw(method, path, body, timeout)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise IncusError(f"non-JSON response: {raw[:500]}")

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, body=None, **kw):
        return self.request("POST", path, body=body, **kw)

    def put(self, path, body=None, **kw):
        return self.request("PUT", path, body=body, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)

    def is_trusted(self):
        return self.get("/1.0").get("metadata", {}).get("auth") == "trusted"

    def wait(self, resp, timeout_s=600):
        """Block on an async operation response until it finishes.

        Incus returns 202 + an operation id for anything long-running (instance
        create, exec, ...). /wait blocks server-side; we still loop because the
        server caps how long a single /wait call parks.
        """
        if resp.get("type") != "async":
            return resp
        if resp.get("error"):
            raise IncusError(f"{resp['error_code']}: {resp['error']}")
        op_id = resp["operation"].split("/operations/")[1].split("?")[0]
        project = ""
        if "project=" in resp["operation"]:
            project = "&project=" + resp["operation"].split("project=")[1].split("&")[0]
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            r = self.get(
                f"/1.0/operations/{op_id}/wait?timeout=30{project}",
                timeout=45,
            )
            md = r.get("metadata") or {}
            status = md.get("status")
            if status == "Success":
                return md
            if status in ("Failure", "Cancelled"):
                raise IncusError(f"operation {status}: {md.get('err') or r.get('error')}")
        raise IncusError(f"operation did not finish within {timeout_s}s")

    def exec(self, instance, command, project="vpp", timeout_s=1800, env=None, cwd=None):
        """Run a command in an instance and return (exit_code, stdout, stderr).

        Uses record-output rather than the interactive websocket path: the
        stdlib has no websocket client, and for scripted runs we only need the
        captured output, not a live tty.
        """
        body = {
            "command": command if isinstance(command, list) else ["sh", "-c", command],
            "wait-for-websocket": False,
            "record-output": True,
            "interactive": False,
        }
        if env:
            body["environment"] = env
        if cwd:
            body["cwd"] = cwd
        md = self.wait(
            self.post(f"/1.0/instances/{instance}/exec?project={project}", body),
            timeout_s=timeout_s,
        )
        meta = md.get("metadata") or {}
        out = meta.get("output") or {}

        def fetch(key):
            path = out.get(key)
            if not path:
                return ""
            return self.request_raw("GET", f"{path}?project={project}")

        return meta.get("return", -1), fetch("1"), fetch("2")

    def push_file(self, instance, local_path, remote_path, project="vpp",
                  mode="0644", uid=0, gid=0, timeout_s=3600):
        """Upload a file into an instance, streaming from disk.

        http.client will stream a file object body in chunks given an explicit
        Content-Length, so multi-GB payloads never sit in memory here.
        """
        local_path = Path(local_path)
        size = local_path.stat().st_size
        conn = http.client.HTTPSConnection(
            self.host, self.port, context=self.ctx, timeout=timeout_s
        )
        try:
            with open(local_path, "rb") as fh:
                # quote() the path: this project's tree lives under a directory
                # literally named "vanilla++", and a raw "+" in a query string
                # decodes to a space, which 404s.
                conn.putrequest(
                    "POST",
                    f"/1.0/instances/{instance}/files"
                    f"?path={quote(str(remote_path), safe='/')}&project={project}",
                )
                conn.putheader("Content-Type", "application/octet-stream")
                conn.putheader("Content-Length", str(size))
                conn.putheader("X-Incus-Type", "file")
                conn.putheader("X-Incus-Mode", mode)
                conn.putheader("X-Incus-UID", str(uid))
                conn.putheader("X-Incus-GID", str(gid))
                conn.endheaders()
                conn.send(fh)
            resp = conn.getresponse()
            raw = resp.read().decode(errors="replace")
        finally:
            conn.close()
        if resp.status not in (200, 201, 202):
            raise IncusError(f"push failed ({resp.status}): {raw[:500]}")
        return size

    def run(self, instance, command, project="vpp", check=True, quiet=False, **kw):
        """exec() plus echoing and optional raising - the ergonomic wrapper."""
        rc, out, err = self.exec(instance, command, project=project, **kw)
        if not quiet:
            if out.strip():
                print(out.rstrip())
            if err.strip():
                print(err.rstrip(), file=sys.stderr)
        if check and rc != 0:
            raise IncusError(f"command failed (rc={rc}): {command}\n{err[:2000]}")
        return rc, out, err


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    method, path = sys.argv[1].upper(), sys.argv[2]
    body = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    print(json.dumps(Incus().request(method, path, body), indent=2))


if __name__ == "__main__":
    main()
