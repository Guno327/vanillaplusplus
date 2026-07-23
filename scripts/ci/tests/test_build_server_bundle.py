"""Fast-tier, stdlib-only, no-network unit tests for build_server_bundle.py's
GitHub #141 unbundling change: the released server zip must no longer
contain any third-party mod jar (everything without a `local_path` in
pack/mods.lock.json), and must instead ship install_mods.py +
server-mods.lock.json for the operator to run.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import build_server_bundle  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _mod(slug, filename, side="both", local_path=None, sha1="a" * 40, url=None):
    m = {
        "slug": slug,
        "project_id": slug,
        "filename": filename,
        "url": url or f"https://cdn.example/{filename}",
        "hashes": {"sha1": sha1, "sha512": "b" * 128},
        "filesize": 123,
        "side": side,
    }
    if local_path:
        m["local_path"] = local_path
    return m


class TestThirdPartyJarFilenames(unittest.TestCase):
    def test_excludes_only_non_local_entries(self):
        lock = {
            "mods": [
                _mod("create", "create.jar"),
                _mod("vppintegration", "vppintegration.jar", local_path="mods-src/vppintegration/build/libs/vppintegration.jar"),
            ]
        }
        excluded = build_server_bundle.third_party_jar_filenames(lock)
        self.assertIn("create.jar", excluded)
        self.assertNotIn("vppintegration.jar", excluded)

    def test_client_only_entries_still_counted_as_third_party(self):
        # side filtering isn't this function's job (build_server.py already
        # keeps client-only jars out of server/mods/ entirely) - it should
        # still report them as non-local if asked, harmlessly.
        lock = {"mods": [_mod("clientmod", "clientmod.jar", side="client")]}
        excluded = build_server_bundle.third_party_jar_filenames(lock)
        self.assertIn("clientmod.jar", excluded)


class TestServerModsLock(unittest.TestCase):
    def test_drops_local_and_client_only_entries(self):
        lock = {
            "mods": [
                _mod("create", "create.jar", side="both"),
                _mod("krypton-fnp", "krypton.jar", side="server"),
                _mod("clientmod", "clientmod.jar", side="client"),
                _mod("vppintegration", "vppintegration.jar", local_path="mods-src/vppintegration/x.jar"),
            ]
        }
        trimmed = build_server_bundle.server_mods_lock(lock)
        slugs = {m["slug"] for m in trimmed["mods"]}
        self.assertEqual(slugs, {"create", "krypton-fnp"})

    def test_trimmed_entries_only_expose_installer_fields(self):
        lock = {"mods": [_mod("create", "create.jar", url="https://cdn.example/create.jar", sha1="c" * 40)]}
        trimmed = build_server_bundle.server_mods_lock(lock)
        entry = trimmed["mods"][0]
        self.assertEqual(entry["filename"], "create.jar")
        self.assertEqual(entry["url"], "https://cdn.example/create.jar")
        self.assertEqual(entry["hashes"], {"sha1": "c" * 40})
        # No sha512/filesize/side/note bloat - installer only needs sha1.
        self.assertNotIn("sha512", entry["hashes"])
        self.assertNotIn("filesize", entry)

    def test_matches_real_lockfile_shape(self):
        # Sanity: server_mods_lock() must not choke on the real lockfile,
        # and must produce at least one entry (the real pack always has
        # server-side third-party mods).
        real_lock = json.loads((REPO_ROOT / "pack" / "mods.lock.json").read_text())
        trimmed = build_server_bundle.server_mods_lock(real_lock)
        self.assertGreater(len(trimmed["mods"]), 0)
        for entry in trimmed["mods"]:
            self.assertTrue(entry["url"].startswith("https://"))
            self.assertEqual(len(entry["hashes"]["sha1"]), 40)


class TestShouldInclude(unittest.TestCase):
    def test_third_party_mod_jar_excluded(self):
        exclude = frozenset({"create.jar"})
        path = build_server_bundle.SERVER / "mods" / "create.jar"
        self.assertFalse(build_server_bundle.should_include(path, exclude))

    def test_local_custom_mod_jar_included(self):
        exclude = frozenset({"create.jar"})  # vppintegration.jar not in this set
        path = build_server_bundle.SERVER / "mods" / "vppintegration.jar"
        self.assertTrue(build_server_bundle.should_include(path, exclude))

    def test_non_mods_files_unaffected_by_exclude_set(self):
        exclude = frozenset({"server.properties"})  # pathological: same name, wrong dir
        path = build_server_bundle.SERVER / "server.properties"
        self.assertTrue(build_server_bundle.should_include(path, exclude))

    def test_preexisting_exclusions_still_enforced(self):
        exclude = frozenset()
        self.assertFalse(build_server_bundle.should_include(build_server_bundle.SERVER / "eula.txt", exclude))
        self.assertFalse(build_server_bundle.should_include(build_server_bundle.SERVER / "world" / "level.dat", exclude))
        self.assertFalse(build_server_bundle.should_include(build_server_bundle.SERVER / "logs" / "latest.log", exclude))


class TestReadmeAndBundleContents(unittest.TestCase):
    def test_readme_documents_install_mods_step(self):
        readme = build_server_bundle.build_readme()
        self.assertIn("install_mods.py", readme)
        self.assertIn("server-mods.lock.json", readme)

    def test_install_mods_script_exists_and_is_self_contained(self):
        # Shipped standalone inside the zip - must not import anything else
        # from this repo's scripts/ tree.
        src = (REPO_ROOT / "scripts" / "install_mods.py").read_text()
        self.assertNotIn("import build_server", src)
        self.assertNotIn("from build_server", src)
        self.assertIn("sha1", src)


if __name__ == "__main__":
    unittest.main()
