import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import build_mrpack  # noqa: E402


def _mod(slug, url, side="both", filesize=100):
    return {
        "slug": slug,
        "side": side,
        "filename": f"{slug}.jar",
        "url": url,
        "hashes": {"sha1": "a" * 40, "sha512": "b" * 128},
        "filesize": filesize,
    }


class TestClassifyMods(unittest.TestCase):
    def test_modrinth_cdn_mod_is_downloadable(self):
        mod = _mod("create", "https://cdn.modrinth.com/data/AAAA/versions/BBBB/create.jar")
        downloadable, bundled = build_mrpack.classify_mods([mod])
        self.assertEqual(downloadable, [mod])
        self.assertEqual(bundled, [])

    def test_non_modrinth_host_is_bundled(self):
        # Regression: uploading a version whose modrinth.index.json
        # references a non-allowlisted download host (e.g. CurseForge's
        # forgecdn.net) is rejected outright by Modrinth's real API
        # ("File download source is not from allowed sources"). Any mod
        # not hosted on cdn.modrinth.com must be bundled instead.
        mod = _mod("ftb-library", "https://mediafilez.forgecdn.net/files/8226/923/ftb-library.jar")
        downloadable, bundled = build_mrpack.classify_mods([mod])
        self.assertEqual(downloadable, [])
        self.assertEqual(bundled, [mod])

    def test_mixed_lock_splits_correctly(self):
        cdn_mod = _mod("create", "https://cdn.modrinth.com/data/AAAA/versions/BBBB/create.jar")
        curseforge_mod = _mod("allthemodium", "https://mediafilez.forgecdn.net/files/7974/403/allthemodium.jar")
        downloadable, bundled = build_mrpack.classify_mods([cdn_mod, curseforge_mod])
        self.assertEqual(downloadable, [cdn_mod])
        self.assertEqual(bundled, [curseforge_mod])

    def test_similar_but_different_host_is_not_mistaken_for_modrinth(self):
        # e.g. a lookalike/subdomain host should not slip past the check
        mod = _mod("evil", "https://cdn.modrinth.com.evil.example/x.jar")
        downloadable, bundled = build_mrpack.classify_mods([mod])
        self.assertEqual(downloadable, [])
        self.assertEqual(bundled, [mod])


if __name__ == "__main__":
    unittest.main()
