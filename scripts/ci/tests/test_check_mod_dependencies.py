"""Unit tests for check_mod_dependencies — the launch-time dependency check
added after the v0.5.0 regression (a client-only missing required dep that
every server-side boot tier could not see). The pure `resolve()` logic and
the jar-toml parser are exercised here with synthetic fixtures, so fast-tier
covers the logic even though the real check needs the mod jars."""
import io
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_mod_dependencies as cmd  # noqa: E402


def _mod(slug, provided, required):
    return {"slug": slug, "provided": set(provided), "required": required}


def _req(modid, version_range="[1,)"):
    return {"modId": modid, "versionRange": version_range, "enforced": version_range is not None}


class TestResolve(unittest.TestCase):
    def test_satisfied_dependency_passes(self):
        mods = [
            _mod("a", ["a"], [_req("b")]),
            _mod("b", ["b"], []),
        ]
        self.assertEqual(cmd.resolve(mods), [])

    def test_missing_required_dependency_is_reported(self):
        # This is the v0.5.0 case: sodium-options-api requires reeses which
        # is not installed.
        mods = [_mod("sodium-options-api", ["sodiumoptionsapi"],
                     [_req("reeses_sodium_options", "*")])]
        problems = cmd.resolve(mods)
        self.assertTrue(any("reeses_sodium_options" in p for p in problems))

    def test_platform_ids_are_always_provided(self):
        mods = [_mod("a", ["a"], [_req("neoforge"), _req("minecraft")])]
        self.assertEqual(cmd.resolve(mods), [])

    def test_dependency_provided_via_jarinjar_passes(self):
        # Create bundles flywheel/ponder as JIJ - parse_mod_jar folds those
        # into `provided`, so resolve() just sees them present.
        mods = [
            _mod("create", ["create", "flywheel", "ponder"], []),
            _mod("iris-flw-compat", ["irisflwcompat"], [_req("flywheel")]),
        ]
        self.assertEqual(cmd.resolve(mods), [])

    def test_malformed_dep_without_versionrange_is_not_enforced(self):
        # stellaris' sky_aesthetics: type=required but no versionRange ->
        # enforced=False -> NeoForge ignores it -> we must NOT flag it.
        dep = {"modId": "sky_aesthetics", "versionRange": None, "enforced": False}
        mods = [_mod("stellaris", ["stellaris"], [dep])]
        self.assertEqual(cmd.resolve(mods), [])

    def test_allowlisted_missing_dep_is_not_reported(self):
        # Even if it were (wrongly) marked enforced, the explicit allowlist
        # covers sky_aesthetics.
        self.assertIn("sky_aesthetics", cmd.KNOWN_UNPROVIDED_OK)
        mods = [_mod("stellaris", ["stellaris"], [_req("sky_aesthetics", "[1,)")])]
        self.assertEqual(cmd.resolve(mods), [])

    def test_case_insensitive_modid_matching(self):
        mods = [
            _mod("a", ["SomeMod"], [_req("somemod")]),
            _mod("b", ["b"], [_req("SOMEMOD")]),
        ]
        self.assertEqual(cmd.resolve(mods), [])


class TestParseModJar(unittest.TestCase):
    def _jar(self, toml_text, jij=None):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("META-INF/neoforge.mods.toml", toml_text)
            for name, sub_toml in (jij or {}).items():
                sub = io.BytesIO()
                with zipfile.ZipFile(sub, "w") as sz:
                    sz.writestr("META-INF/neoforge.mods.toml", sub_toml)
                z.writestr(f"META-INF/jarjar/{name}", sub.getvalue())
        return buf.getvalue()

    def test_parses_provided_modid_and_required_dep(self):
        toml = '''
[[mods]]
modId="examplemod"
[[dependencies."examplemod"]]
modId="reeses_sodium_options"
type="required"
versionRange="*"
side="BOTH"
'''
        provided, required = cmd.parse_mod_jar(self._jar(toml))
        self.assertIn("examplemod", provided)
        self.assertEqual(len(required), 1)
        self.assertEqual(required[0]["modId"], "reeses_sodium_options")
        self.assertTrue(required[0]["enforced"])

    def test_mandatory_true_legacy_field_is_required(self):
        toml = '''
[[mods]]
modId="m"
[[dependencies."m"]]
modId="dep"
mandatory=true
versionRange="[1,)"
'''
        _, required = cmd.parse_mod_jar(self._jar(toml))
        self.assertEqual(len(required), 1)
        self.assertTrue(required[0]["enforced"])

    def test_required_without_versionrange_is_parsed_as_not_enforced(self):
        toml = '''
[[mods]]
modId="stellaris"
[[dependencies."stellaris"]]
modId="sky_aesthetics"
type="required"
'''
        _, required = cmd.parse_mod_jar(self._jar(toml))
        self.assertEqual(len(required), 1)
        self.assertFalse(required[0]["enforced"])

    def test_optional_dependency_is_not_collected(self):
        toml = '''
[[mods]]
modId="m"
[[dependencies."m"]]
modId="opt"
type="optional"
versionRange="[1,)"
'''
        _, required = cmd.parse_mod_jar(self._jar(toml))
        self.assertEqual(required, [])

    def test_jarinjar_bundled_modid_is_provided(self):
        toml = '[[mods]]\nmodId="create"\n'
        jij_toml = '[[mods]]\nmodId="flywheel"\n'
        provided, _ = cmd.parse_mod_jar(self._jar(toml, jij={"flywheel-1.0.jar": jij_toml}))
        self.assertIn("create", provided)
        self.assertIn("flywheel", provided)

    def test_end_to_end_reeses_case_fails_resolution(self):
        # Full loop: a jar declaring the reeses dep, with no provider, must
        # surface as a resolve() problem.
        toml = '''
[[mods]]
modId="sodiumoptionsapi"
[[dependencies."sodiumoptionsapi"]]
modId="reeses_sodium_options"
mandatory=true
versionRange="*"
side="BOTH"
'''
        provided, required = cmd.parse_mod_jar(self._jar(toml))
        problems = cmd.resolve([{"slug": "sodium-options-api", "provided": provided, "required": required}])
        self.assertEqual(len(problems), 1)
        self.assertIn("reeses_sodium_options", problems[0])


if __name__ == "__main__":
    unittest.main()
