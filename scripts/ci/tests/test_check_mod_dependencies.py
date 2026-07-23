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


def _class_jar(entries, toml_text=None, jij=None):
    """Build an in-memory jar with .class files at the given paths (a list of
    "a/b/C.class"-style strings), an optional main mods.toml, and optional
    JIJ sub-jars: {filename: (entries, toml_text)}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        if toml_text is not None:
            z.writestr("META-INF/neoforge.mods.toml", toml_text)
        for path in entries:
            z.writestr(path, b"")
        for name, (sub_entries, sub_toml) in (jij or {}).items():
            z.writestr(f"META-INF/jarjar/{name}", _class_jar(sub_entries, sub_toml))
    return buf.getvalue()


class TestSplitPackageDetection(unittest.TestCase):
    """The v0.5.1 regression: sodium-dynamic-lights directly shades
    dev.lambdaurora.lambdynlights.api(.item), and ars-nouveau Jar-in-Jars its
    own copy of lambdynlights_api exporting the same two packages ->
    java.lang.module.ResolutionException at launch. Fixtures below mirror
    the real jar shapes ground-truthed against the actual pinned jars."""

    def test_real_lambdynlights_conflict_is_flagged(self):
        sodium_dynamic_lights = _class_jar(
            [
                "dev/lambdaurora/lambdynlights/api/DynamicLightHandler.class",
                "dev/lambdaurora/lambdynlights/api/DynamicLightHandlers.class",
                "dev/lambdaurora/lambdynlights/api/item/ItemLightSource.class",
            ],
            toml_text='[[mods]]\nmodId="sodiumdynamiclights"\n',
        )
        ars_nouveau = _class_jar(
            ["com/hollingsworth/arsnouveau/Placeholder.class"],
            toml_text='[[mods]]\nmodId="ars_nouveau"\n',
            jij={
                "lambdynamiclights-api-4.5.1.jar": (
                    [
                        "dev/lambdaurora/lambdynlights/api/DynamicLightHandler.class",
                        "dev/lambdaurora/lambdynlights/api/item/ItemLightSource.class",
                    ],
                    '[[mods]]\nmodId="lambdynlights_api"\n',
                ),
            },
        )
        all_entities = []
        e1, _ = cmd.collect_entities_and_ats(sodium_dynamic_lights, "sodium-dynamic-lights")
        e2, _ = cmd.collect_entities_and_ats(ars_nouveau, "ars-nouveau")
        all_entities.extend(e1)
        all_entities.extend(e2)

        problems = cmd.detect_split_packages(all_entities)
        self.assertEqual(len(problems), 2)
        self.assertTrue(any("dev.lambdaurora.lambdynlights.api'" in p for p in problems))
        self.assertTrue(any("dev.lambdaurora.lambdynlights.api.item" in p for p in problems))
        self.assertTrue(any("sodium-dynamic-lights" in p and "ars-nouveau" in p for p in problems))

    def test_post_hotfix_set_without_sodium_dynamic_lights_passes(self):
        # Removing sodium-dynamic-lights (the real fix) leaves ars-nouveau's
        # JIJ'd copy as the only exporter -> no conflict.
        ars_nouveau = _class_jar(
            ["com/hollingsworth/arsnouveau/Placeholder.class"],
            toml_text='[[mods]]\nmodId="ars_nouveau"\n',
            jij={
                "lambdynamiclights-api-4.5.1.jar": (
                    ["dev/lambdaurora/lambdynlights/api/DynamicLightHandler.class"],
                    '[[mods]]\nmodId="lambdynlights_api"\n',
                ),
            },
        )
        entities, _ = cmd.collect_entities_and_ats(ars_nouveau, "ars-nouveau")
        self.assertEqual(cmd.detect_split_packages(entities), [])

    def test_same_modid_jarinjar_bundles_are_not_flagged(self):
        # The real, currently-installed case: `create` and `iris-flw-compat`
        # both Jar-in-Jar a copy of flywheel under DIFFERENT Maven
        # coordinates but the SAME declared modId "flywheel" - NeoForge's
        # own Jar-in-Jar selection keeps exactly one physical copy, so this
        # must NOT be flagged as a split package.
        create = _class_jar(
            ["com/simibubi/create/Placeholder.class"],
            toml_text='[[mods]]\nmodId="create"\n',
            jij={
                "flywheel-neoforge-1.21.1-1.0.6.jar": (
                    ["dev/engine_room/flywheel/api/Backend.class"],
                    '[[mods]]\nmodId="flywheel"\n',
                ),
            },
        )
        iris_flw_compat = _class_jar(
            ["top/leonx/irisflw/Placeholder.class"],
            toml_text='[[mods]]\nmodId="irisflw"\n',
            jij={
                "neoforge.jar": (
                    ["dev/engine_room/flywheel/api/Backend.class"],
                    '[[mods]]\nmodId="flywheel"\n',
                ),
            },
        )
        e1, _ = cmd.collect_entities_and_ats(create, "create")
        e2, _ = cmd.collect_entities_and_ats(iris_flw_compat, "iris-flw-compat")
        self.assertEqual(cmd.detect_split_packages(e1 + e2), [])

    def test_two_independent_mods_shading_same_package_directly_is_flagged(self):
        # Neither side uses Jar-in-Jar / declares a matching modId for the
        # shared package - two genuinely distinct, undeduplicatable mods.
        mod_a = _class_jar(["com/example/shaded/lib/Thing.class"],
                            toml_text='[[mods]]\nmodId="moda"\n')
        mod_b = _class_jar(["com/example/shaded/lib/Thing.class"],
                            toml_text='[[mods]]\nmodId="modb"\n')
        e1, _ = cmd.collect_entities_and_ats(mod_a, "mod-a")
        e2, _ = cmd.collect_entities_and_ats(mod_b, "mod-b")
        problems = cmd.detect_split_packages(e1 + e2)
        self.assertEqual(len(problems), 1)
        self.assertIn("com.example.shaded.lib", problems[0])

    def test_platform_packages_are_never_flagged(self):
        mod_a = _class_jar(["net/minecraft/client/Minecraft.class"],
                            toml_text='[[mods]]\nmodId="moda"\n')
        mod_b = _class_jar(["net/minecraft/client/Minecraft.class"],
                            toml_text='[[mods]]\nmodId="modb"\n')
        e1, _ = cmd.collect_entities_and_ats(mod_a, "mod-a")
        e2, _ = cmd.collect_entities_and_ats(mod_b, "mod-b")
        self.assertEqual(cmd.detect_split_packages(e1 + e2), [])

    def test_single_mod_own_package_is_never_a_conflict(self):
        mod_a = _class_jar(["com/example/Thing.class"],
                            toml_text='[[mods]]\nmodId="moda"\n')
        entities, _ = cmd.collect_entities_and_ats(mod_a, "mod-a")
        self.assertEqual(cmd.detect_split_packages(entities), [])


class TestAccessTransformerCheck(unittest.TestCase):
    """The other half of the v0.5.1 incident log: "Access transformer file
    accesstransformer.cfg provided by mod irisflw does not exist!" - a mod
    declares [[accessTransformers]] file=... but doesn't actually ship it."""

    def test_missing_at_file_is_flagged(self):
        toml = '''
[[mods]]
modId="irisflw"
[[accessTransformers]]
file="accesstransformer.cfg"
'''
        jar = _class_jar(["top/leonx/irisflw/Placeholder.class"], toml_text=toml)
        _, at_records = cmd.collect_entities_and_ats(jar, "iris-flw-compat")
        problems = cmd.check_access_transformers(at_records)
        self.assertEqual(len(problems), 1)
        self.assertIn("accesstransformer.cfg", problems[0])

    def test_present_at_file_is_not_flagged(self):
        toml = '''
[[mods]]
modId="irisflw"
[[accessTransformers]]
file="accesstransformer.cfg"
'''
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("META-INF/neoforge.mods.toml", toml)
            z.writestr("META-INF/accesstransformer.cfg", "public net.minecraft.Foo f\n")
        _, at_records = cmd.collect_entities_and_ats(buf.getvalue(), "iris-flw-compat")
        self.assertEqual(cmd.check_access_transformers(at_records), [])

    def test_commented_out_block_is_not_a_false_declaration(self):
        # Real case: create-tfmg/create-marketplace/create-central-kitchen
        # ship this entire block commented out as unused boilerplate. A
        # naive substring search for '[[accessTransformers' still matches
        # inside the comment and must NOT be treated as a real declaration.
        toml = '''
[[mods]]
modId="createtfmg"
#[[accessTransformers]]
#    file="META-INF/accesstransformer.cfg"
'''
        jar = _class_jar(["com/example/Placeholder.class"], toml_text=toml)
        _, at_records = cmd.collect_entities_and_ats(jar, "create-tfmg")
        self.assertEqual(at_records, [])

    def test_declared_file_without_meta_inf_prefix_resolves_there(self):
        # NeoForge resolves a bare filename relative to META-INF/.
        toml = '''
[[mods]]
modId="m"
[[accessTransformers]]
file="accesstransformer.cfg"
'''
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("META-INF/neoforge.mods.toml", toml)
            z.writestr("META-INF/accesstransformer.cfg", "")
        _, at_records = cmd.collect_entities_and_ats(buf.getvalue(), "m")
        self.assertEqual(cmd.check_access_transformers(at_records), [])


if __name__ == "__main__":
    unittest.main()
