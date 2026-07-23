import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import audit_progression as ap  # noqa: E402


class TagRegistryTests(unittest.TestCase):
    def test_resolve_flat_tag(self):
        reg = ap.TagRegistry()
        reg.add_tag_file("c:ingots/iron", {"values": ["minecraft:iron_ingot"]})
        self.assertEqual(reg.resolve("c:ingots/iron"), frozenset({"minecraft:iron_ingot"}))

    def test_resolve_tag_of_tag(self):
        reg = ap.TagRegistry()
        reg.add_tag_file("c:ingots/iron", {"values": ["minecraft:iron_ingot"]})
        reg.add_tag_file("c:ingots", {"values": ["#c:ingots/iron", "minecraft:gold_ingot"]})
        self.assertEqual(
            reg.resolve("c:ingots"),
            frozenset({"minecraft:iron_ingot", "minecraft:gold_ingot"}),
        )

    def test_unresolved_tag_is_empty(self):
        reg = ap.TagRegistry()
        self.assertEqual(reg.resolve("c:nonexistent"), frozenset())

    def test_cyclic_tag_does_not_hang(self):
        reg = ap.TagRegistry()
        reg.add_tag_file("c:a", {"values": ["#c:b"]})
        reg.add_tag_file("c:b", {"values": ["#c:a", "minecraft:stick"]})
        # Should terminate and at least surface the non-cyclic member.
        self.assertIn("minecraft:stick", reg.resolve("c:b"))


class IngredientSpecTests(unittest.TestCase):
    def test_shapeless_ingredients(self):
        recipe = {
            "type": "minecraft:crafting_shapeless",
            "ingredients": [{"item": "minecraft:stick"}, {"tag": "c:ingots/iron"}],
            "result": {"id": "minecraft:iron_pickaxe"},
        }
        specs = ap.recipe_ingredient_specs(recipe)
        self.assertIn(("item", "minecraft:stick"), specs)
        self.assertIn(("tag", "c:ingots/iron"), specs)

    def test_shaped_key(self):
        recipe = {
            "type": "minecraft:crafting_shaped",
            "key": {"A": {"item": "create:andesite_alloy"}, "B": {"tag": "c:nuggets/iron"}},
            "result": {"id": "create:brass_hand"},
        }
        specs = ap.recipe_ingredient_specs(recipe)
        self.assertEqual(
            set(specs), {("item", "create:andesite_alloy"), ("tag", "c:nuggets/iron")}
        )

    def test_nested_alternatives_become_oneof(self):
        recipe = {
            "type": "create:deploying",
            "ingredients": [
                {"item": "create:incomplete_track"},
                [{"tag": "c:nuggets/iron"}, {"tag": "c:nuggets/zinc"}],
            ],
            "results": [{"id": "create:incomplete_track"}],
        }
        specs = ap.recipe_ingredient_specs(recipe)
        oneofs = [s for s in specs if s[0] == "oneof"]
        self.assertEqual(len(oneofs), 1)
        self.assertEqual(
            set(oneofs[0][1]), {("tag", "c:nuggets/iron"), ("tag", "c:nuggets/zinc")}
        )

    def test_sequenced_assembly_walks_steps(self):
        recipe = {
            "type": "create:sequenced_assembly",
            "ingredient": {"tag": "create:sleepers"},
            "results": [{"id": "create:track"}],
            "sequence": [
                {
                    "type": "create:deploying",
                    "ingredients": [{"item": "create:incomplete_track"}],
                    "results": [{"id": "create:incomplete_track"}],
                }
            ],
        }
        specs = ap.recipe_ingredient_specs(recipe)
        self.assertIn(("tag", "create:sleepers"), specs)
        self.assertIn(("item", "create:incomplete_track"), specs)

    def test_result_never_treated_as_ingredient(self):
        recipe = {
            "type": "minecraft:smelting",
            "ingredient": {"item": "minecraft:raw_iron"},
            "result": {"id": "minecraft:iron_ingot"},
        }
        specs = ap.recipe_ingredient_specs(recipe)
        self.assertNotIn(("item", "minecraft:iron_ingot"), specs)

    def test_kubejs_tag_shorthand_string(self):
        recipe = {
            "key": {"C": "#c:storage_blocks/copper", "A": "create:andesite_alloy"},
            "result": {"id": "x"},
        }
        specs = ap.recipe_ingredient_specs(recipe)
        self.assertIn(("tag", "c:storage_blocks/copper"), specs)
        self.assertIn(("item", "create:andesite_alloy"), specs)


class ExtractResultIdsTests(unittest.TestCase):
    def test_string_result(self):
        self.assertEqual(
            ap.extract_result_ids({"result": "refinedstorage:controller"}),
            ["refinedstorage:controller"],
        )

    def test_dict_result(self):
        self.assertEqual(
            ap.extract_result_ids({"result": {"id": "create:track_station", "count": 2}}),
            ["create:track_station"],
        )

    def test_results_list(self):
        ids = ap.extract_result_ids({"results": [{"id": "create:crushed_raw_nickel"}, {"id": "create:experience_nugget"}]})
        self.assertEqual(ids, ["create:crushed_raw_nickel", "create:experience_nugget"])


# ---------------------------------------------------------------------------
# Regression tests for the two known #56 false positives. Fixtures are the
# REAL recipe JSON read out of the pinned jars (create-1.21.1-6.0.10.jar /
# refinedstorage-neoforge-2.0.9.jar) during development - see this test
# file's own history / PR description for how they were captured.
# ---------------------------------------------------------------------------
class FalsePositiveRegressionTests(unittest.TestCase):
    def _index(self, recipes):
        index = ap.RecipeIndex()
        for i, r in enumerate(recipes):
            index.add(r, recipe_id=f"test:recipe_{i}")
        return index

    def test_track_station_needs_railway_casing_not_track(self):
        # create:track_station's REAL recipe (data/create/recipe/crafting/
        # kinetics/track_station.json): shapeless, railway_casing + compass.
        track_station_recipe = {
            "type": "minecraft:crafting_shapeless",
            "ingredients": [{"item": "create:railway_casing"}, {"item": "minecraft:compass"}],
            "result": {"count": 2, "id": "create:track_station"},
        }
        # A DIFFERENT, unrelated recipe that a substring/filename-based
        # matcher could confuse it with: create:track itself (a
        # sequenced_assembly keyed off cheap sleepers/nuggets, real id
        # "create:track" - similar name, NOT track_station).
        track_recipe = {
            "type": "create:sequenced_assembly",
            "ingredient": {"tag": "create:sleepers"},
            "results": [{"id": "create:track"}],
            "sequence": [
                {
                    "type": "create:deploying",
                    "ingredients": [{"tag": "c:nuggets/iron"}],
                    "results": [{"id": "create:incomplete_track"}],
                }
            ],
        }
        # railway_casing needs a real tier marker (brass_ingot), so
        # track_station should compute to brass_age, NOT rootborn/andesite.
        railway_casing_recipe = {
            "type": "minecraft:crafting_shaped",
            "key": {"B": {"item": "create:brass_ingot"}, "W": {"tag": "minecraft:planks"}},
            "result": {"id": "create:railway_casing"},
        }
        index = self._index([track_station_recipe, track_recipe, railway_casing_recipe])
        tags = ap.TagRegistry()
        tags.add_tag_file("minecraft:planks", {"values": ["minecraft:oak_planks"]})

        tier = ap.compute_item_tier("create:track_station", index, tags)
        self.assertEqual(
            ap.TIER_ORDER[tier], "brass_age",
            "track_station must be gated by its real railway_casing "
            "ingredient (brass_age), not misidentified via the unrelated "
            "create:track recipe (which would compute rootborn/andesite)",
        )

    def test_refinedstorage_controller_ignores_recoloring_recipe(self):
        # RS's own controller recoloring recipes (one per dye colour) -
        # one of them (the "restore to base colour" case) literally has
        # "result": "refinedstorage:controller", which is what fooled the
        # #56 audit. type must be excluded outright.
        recoloring_recipe = {
            "type": "refinedstorage:recoloring",
            "dye": {"tag": "c:dyes/light_blue"},
            "ingredient": {"tag": "refinedstorage:controllers"},
            "result": "refinedstorage:controller",
        }
        # RS's REAL controller recipe: crafting_shaped needing an
        # advanced_processor (itself needing a diamond - no tier marker in
        # this pack, so this whole chain computes to rootborn - a
        # separate, real finding this audit is expected to surface, not a
        # bug in the audit itself; the point of THIS test is narrower:
        # confirm the recoloring recipe is never the one consulted).
        real_recipe = {
            "type": "minecraft:crafting_shaped",
            "key": {
                "E": {"item": "refinedstorage:quartz_enriched_iron"},
                "P": {"item": "refinedstorage:advanced_processor"},
                "S": {"tag": "c:silicon"},
                "M": {"item": "refinedstorage:machine_casing"},
            },
            "result": {"id": "refinedstorage:controller"},
        }
        index = self._index([recoloring_recipe, real_recipe])
        self.assertNotIn("refinedstorage:recoloring", index.excluded_types.keys() - index.excluded_types.keys())
        self.assertIn("refinedstorage:recoloring", index.excluded_types)
        # Only the real recipe should be indexed for this output.
        candidates = index.by_output.get("refinedstorage:controller", [])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["type"], "minecraft:crafting_shaped")

    def test_recoloring_recipe_excluded_even_as_sole_recipe(self):
        # If (hypothetically) recoloring were the ONLY recipe found for an
        # item, that item must come back as unreachable-via-recipe (tier 0,
        # same as any other item with no real recipe) rather than silently
        # accepting the recolor as an acquisition path.
        recoloring_only = {
            "type": "refinedstorage:recoloring",
            "ingredient": {"tag": "refinedstorage:controllers"},
            "result": "refinedstorage:pink_controller",
        }
        index = self._index([recoloring_only])
        self.assertEqual(index.by_output.get("refinedstorage:pink_controller"), None)


class TierComputationTests(unittest.TestCase):
    def _index(self, recipes):
        index = ap.RecipeIndex()
        for i, r in enumerate(recipes):
            index.add(r, recipe_id=f"test:recipe_{i}")
        return index

    def test_raw_material_is_rootborn(self):
        index = self._index([])
        tier = ap.compute_item_tier("minecraft:iron_ingot", index, ap.TagRegistry())
        self.assertEqual(ap.TIER_ORDER[tier], "rootborn")

    def test_tier_marker_is_its_own_tier_not_recursed(self):
        # andesite_alloy's real recipe is cheap (andesite + a nugget) - the
        # marker's OWN tier must be andesite_age regardless, by definition.
        index = self._index([{
            "type": "minecraft:crafting_shaped",
            "key": {"A": {"item": "minecraft:andesite"}, "B": {"tag": "c:nuggets/iron"}},
            "result": {"id": "create:andesite_alloy"},
        }])
        tier = ap.compute_item_tier("create:andesite_alloy", index, ap.TagRegistry())
        self.assertEqual(ap.TIER_ORDER[tier], "andesite_age")

    def test_transitive_gate_through_intermediate_item(self):
        # gold_barrel (brass_age gate) requires iron_barrel, which requires
        # andesite_alloy (andesite_age) - max across the chain is brass_age.
        index = self._index([
            {
                "type": "sophisticatedstorage:storage_tier_upgrade",
                "key": {"A": {"item": "create:andesite_alloy"}, "I": {"tag": "c:ingots/iron"}},
                "result": {"id": "sophisticatedstorage:iron_barrel"},
            },
            {
                "type": "sophisticatedstorage:storage_tier_upgrade",
                "key": {
                    "R": {"item": "create:brass_ingot"},
                    "G": {"tag": "c:ingots/gold"},
                    "S": {"item": "sophisticatedstorage:iron_barrel"},
                },
                "result": {"id": "sophisticatedstorage:gold_barrel"},
            },
        ])
        tier = ap.compute_item_tier("sophisticatedstorage:gold_barrel", index, ap.TagRegistry())
        self.assertEqual(ap.TIER_ORDER[tier], "brass_age")

    def test_cheapest_of_multiple_recipes_wins(self):
        index = self._index([
            {"type": "minecraft:crafting_shaped", "key": {"A": {"item": "create:brass_ingot"}}, "result": {"id": "x:thing"}},
            {"type": "minecraft:crafting_shapeless", "ingredients": [{"item": "minecraft:stick"}], "result": {"id": "x:thing"}},
        ])
        tier = ap.compute_item_tier("x:thing", index, ap.TagRegistry())
        self.assertEqual(ap.TIER_ORDER[tier], "rootborn")

    def test_oneof_alternative_can_bypass_a_gate(self):
        # A recipe requiring "brass_ingot OR stick" is NOT actually gated -
        # a player can always pick the cheap alternative.
        index = self._index([{
            "type": "minecraft:crafting_shapeless",
            "ingredients": [[{"item": "create:brass_ingot"}, {"item": "minecraft:stick"}]],
            "result": {"id": "x:thing"},
        }])
        tier = ap.compute_item_tier("x:thing", index, ap.TagRegistry())
        self.assertEqual(ap.TIER_ORDER[tier], "rootborn")

    def test_cyclic_recipe_does_not_hang(self):
        index = self._index([
            {"type": "minecraft:crafting_shapeless", "ingredients": [{"item": "x:b"}], "result": {"id": "x:a"}},
            {"type": "minecraft:crafting_shapeless", "ingredients": [{"item": "x:a"}], "result": {"id": "x:b"}},
        ])
        tier = ap.compute_item_tier("x:a", index, ap.TagRegistry())
        self.assertEqual(tier, 0)

    def test_tag_ingredient_takes_cheapest_member(self):
        index = self._index([
            {"type": "minecraft:crafting_shaped", "key": {"A": {"item": "create:brass_ingot"}}, "result": {"id": "x:gated_ingot"}},
        ])
        tags = ap.TagRegistry()
        tags.add_tag_file("x:ingots", {"values": ["x:gated_ingot", "minecraft:iron_ingot"]})
        # A recipe needing the TAG (not the specific gated item) should be
        # satisfiable with the cheap alternative (iron_ingot has no
        # recipe -> rootborn), even though one tag member is brass_age.
        recipe = {"type": "minecraft:crafting_shapeless", "ingredients": [{"tag": "x:ingots"}], "result": {"id": "x:final"}}
        index.add(recipe)
        tier = ap.compute_item_tier("x:final", index, tags)
        self.assertEqual(ap.TIER_ORDER[tier], "rootborn")


class JsLiteralParsingTests(unittest.TestCase):
    def test_simple_object(self):
        val = ap.js_literal_to_py("{ id: 'create:andesite_alloy', count: 2 }")
        self.assertEqual(val, {"id": "create:andesite_alloy", "count": 2})

    def test_nested_array_and_object(self):
        val = ap.js_literal_to_py("{ key: { A: { item: 'x:y' } }, pattern: ['AB', 'CD'] }")
        self.assertEqual(val["pattern"], ["AB", "CD"])
        self.assertEqual(val["key"]["A"]["item"], "x:y")

    def test_double_quoted_string(self):
        self.assertEqual(ap.js_literal_to_py('"epicfight:iron_dagger"'), "epicfight:iron_dagger")


class KubeJsOverrideTests(unittest.TestCase):
    def _index_from_jars(self, recipes):
        index = ap.RecipeIndex()
        for i, r in enumerate(recipes):
            index.add(r, recipe_id=f"toms_storage:recipe_{i}" if i == 0 else f"test:recipe_{i}")
        return index

    def _write(self, tmp_path, name, content):
        p = tmp_path / name
        p.write_text(content)
        return p

    def test_event_remove_by_id_then_shaped_add(self, ):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            js_dir = Path(td)
            self._write(js_dir, "storage.js", """
ServerEvents.recipes(event => {
    event.remove({ id: 'toms_storage:inventory_connector' })
    event.shaped('toms_storage:inventory_connector', [
        'CDC',
        'CBC',
        'CCC'
    ], {
        B: 'minecraft:chest',
        C: '#c:ingots/iron',
        D: 'minecraft:redstone_torch'
    }).id('vanillaplusplus:inventory_connector_iron_tier')
})
""")
            index = ap.RecipeIndex()
            index.add(
                {"type": "minecraft:crafting_shaped",
                 "key": {"E": {"item": "minecraft:ender_pearl"}, "D": {"tag": "c:gems/diamond"}},
                 "result": {"id": "toms_storage:inventory_connector"}},
                recipe_id="toms_storage:inventory_connector",
            )
            ap.parse_kubejs_overrides(index, js_dir=js_dir)
            candidates = index.by_output["toms_storage:inventory_connector"]
            self.assertEqual(len(candidates), 1)
            self.assertIn(("tag", "c:ingots/iron"), ap.recipe_ingredient_specs(candidates[0]))

    def test_foreach_over_object_array_expands_per_entry(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            js_dir = Path(td)
            self._write(js_dir, "wands.js", """
const WAND_TIERS = [
    { id: 'wands:copper_wand', tip: 'minecraft:copper_ingot', tier: 'create:andesite_alloy', suffix: 'andesite' },
    { id: 'wands:diamond_wand', tip: 'minecraft:diamond', tier: 'create:brass_ingot', suffix: 'brass' },
]
ServerEvents.recipes(event => {
    WAND_TIERS.forEach(wand => {
        event.remove({ output: wand.id })
        event.shaped(wand.id, [
            'A #',
            ' / ',
            '/  '
        ], {
            '#': wand.tip,
            '/': 'minecraft:stick',
            A: wand.tier
        }).id('vanillaplusplus:' + wand.id)
    })
})
""")
            index = ap.RecipeIndex()
            ap.parse_kubejs_overrides(index, js_dir=js_dir)
            self.assertIn(("item", "create:andesite_alloy"),
                          ap.recipe_ingredient_specs(index.by_output["wands:copper_wand"][0]))
            self.assertIn(("item", "create:brass_ingot"),
                          ap.recipe_ingredient_specs(index.by_output["wands:diamond_wand"][0]))

    def test_string_loop_var_colliding_with_json_key_name(self):
        # Regression: tier_gating.js's real SOPH_STORAGE_TYPES loop binds
        # the loop variable to the literal name `type` - which collides
        # with recipe JSON's own `type` field. A naive substitution turns
        # `type: 'sophisticatedstorage:storage_tier_upgrade'` (a JSON key)
        # into `'barrel': '...'`, corrupting the recipe. Loop-variable
        # substitution must only replace VALUE uses of the identifier, not
        # KEY uses of the same spelling.
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            js_dir = Path(td)
            self._write(js_dir, "soph_storage.js", """
const SOPH_STORAGE_TYPES = ['barrel', 'chest']
ServerEvents.recipes(event => {
    SOPH_STORAGE_TYPES.forEach(type => {
        event.remove({ id: `sophisticatedstorage:iron_${type}` })
        event.custom({
            type: 'sophisticatedstorage:storage_tier_upgrade',
            key: {
                I: { tag: 'c:ingots/iron' },
                A: { item: 'create:andesite_alloy' },
                S: { item: `sophisticatedstorage:${type}` }
            },
            result: { count: 1, id: `sophisticatedstorage:iron_${type}` }
        }).id(`vanillaplusplus:iron_${type}_andesite_tier`)
    })
})
""")
            index = ap.RecipeIndex()
            ap.parse_kubejs_overrides(index, js_dir=js_dir)
            recs = index.by_output.get("sophisticatedstorage:iron_barrel", [])
            self.assertEqual(len(recs), 1)
            specs = ap.recipe_ingredient_specs(recs[0])
            self.assertIn(("item", "create:andesite_alloy"), specs)
            self.assertIn(("item", "sophisticatedstorage:barrel"), specs)
            recs2 = index.by_output.get("sophisticatedstorage:iron_chest", [])
            self.assertEqual(len(recs2), 1)
            self.assertIn(("item", "sophisticatedstorage:chest"), ap.recipe_ingredient_specs(recs2[0]))

    def test_unresolved_loop_fallback_reads_entry_as_ingredient_bag(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            js_dir = Path(td)
            self._write(js_dir, "upgrades.js", """
const SOPH_STORAGE_UPGRADE_ITEMS = [
    { id: 'sophisticatedstorage:basic_to_iron_tier_upgrade', pattern: ['III', 'ILI', 'III'], key: { I: { tag: 'c:ingots/iron' }, L: { item: 'minecraft:lever' } }, tierLetter: 'A', tier: 'create:andesite_alloy', suffix: 'andesite_tier' },
    { id: 'sophisticatedstorage:copper_to_gold_tier_upgrade', pattern: ['GGG', 'GTG', 'GGG'], key: { G: { tag: 'c:ingots/gold' }, T: { item: 'sophisticatedstorage:copper_to_iron_tier_upgrade' } }, tierLetter: 'R', tier: 'create:brass_ingot', suffix: 'brass_tier' },
]
ServerEvents.recipes(event => {
    SOPH_STORAGE_UPGRADE_ITEMS.forEach(entry => {
        event.remove({ id: entry.id })
        let newPattern = [entry.pattern[0].replace(/[A-Z]/, entry.tierLetter), entry.pattern[1], entry.pattern[2]]
        let newKey = Object.assign({}, entry.key)
        newKey[entry.tierLetter] = { item: entry.tier }
        event.custom({
            type: 'minecraft:crafting_shaped',
            pattern: newPattern,
            key: newKey,
            result: { count: 1, id: entry.id }
        }).id('vanillaplusplus:' + entry.id + '_' + entry.suffix)
    })
})
""")
            index = ap.RecipeIndex()
            ap.parse_kubejs_overrides(index, js_dir=js_dir)
            specs_a = ap.recipe_ingredient_specs(
                index.by_output["sophisticatedstorage:basic_to_iron_tier_upgrade"][0]
            )
            self.assertIn(("item", "create:andesite_alloy"), specs_a)
            self.assertIn(("tag", "c:ingots/iron"), specs_a)

            specs_b = ap.recipe_ingredient_specs(
                index.by_output["sophisticatedstorage:copper_to_gold_tier_upgrade"][0]
            )
            self.assertIn(("item", "create:brass_ingot"), specs_b)
            self.assertIn(("item", "sophisticatedstorage:copper_to_iron_tier_upgrade"), specs_b)


class LoadAssignedTiersTests(unittest.TestCase):
    def test_reads_real_progression_toml(self):
        assigned = ap.load_assigned_tiers()
        # A couple of ids we know are in the real files.
        self.assertEqual(assigned.get("minecraft:iron_ingot"), "andesite_age")
        self.assertEqual(assigned.get("refinedstorage:controller"), "brass_age")


if __name__ == "__main__":
    unittest.main()
