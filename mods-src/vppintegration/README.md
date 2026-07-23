# VPP Integration: Overgeared x Silent Gear quality bridge

A small NeoForge 1.21.1 mod that lets gear forged through **Overgeared**'s
forging minigame carry its "ForgingQuality" grade onto a **Silent Gear**
tool/weapon/armor part, and makes that quality actually change the item's
final computed stats.

Built for the [Vanilla++ modpack](https://github.com/Guno327/vanillaplusplus)
(GitHub issue #67) as an owner-approved exception to that pack's "no new mods"
rule - the integration cannot be done as data/config/KubeJS (see
`DESIGN.md`'s "GitHub issue #67 investigation" section in the parent repo for
the full feasibility writeup). This mod is tracked as its own independent
source tree so it can be published to Modrinth on its own, separate from the
modpack it was built for.

## What it does

- Overgeared's own quality-to-attribute-bonus layer
  (`net.stirdrem.overgeared.event.QualityAttributeHandler`, an
  `ItemAttributeModifierEvent` listener at `LOWEST` priority, already shipped
  in the Overgeared jar) is **pure data** and works on any item regardless of
  who made it - Silent Gear items included, with zero code from this mod.
  This mod ships `data/overgeared/quality_attributes/silentgear_*.json` so
  that layer actually targets Silent Gear's weapon/armor item tags.
- What Overgeared genuinely cannot do on its own is put a *correct* material
  assignment on a Silent Gear part in the first place: its forging recipes
  are static, one-recipe-per-material JSON with a fixed result item, while
  Silent Gear's material assignment is a data component
  (`SgDataComponents.MATERIAL_LIST`) that only Silent Gear's own
  recipe/stat-computation code populates and interprets. This mod ships
  `data/overgeared/recipe/forging/*_silentgear.json` recipes whose `result`
  is a real Silent Gear part item with Silent Gear's default/empty material,
  and a mixin
  (`dev.vanillaplusplus.vppintegration.mixin.AbstractSmithingAnvilBlockEntityMixin`)
  that corrects the material at craft time using Silent Gear's own real
  material-detection API (`MaterialInstance.from(ItemStack)`, which already
  returns the built `MaterialInstance` in one call), then asks Silent Gear to
  recompute stats (`GearData.recalculateGearData`) - not a guess at the
  private codec.
- Silent Gear's own non-vanilla-attribute stats (durability, harvest speed -
  its own `GearPropertyMap`/`GearPropertiesData` system, separate from
  vanilla Attributes) get a quality-scaled bonus from
  `dev.vanillaplusplus.vppintegration.quality.OvergearedSilentGearBridge`,
  reusing Overgeared's own per-quality config bonus values
  (`ServerConfig.*_DURABILITY_BONUS` / `*_MINING_SPEED_BONUS`) for symmetry
  with Overgeared's native items. This bridge rewrites the item's computed
  `GEAR_PROPERTIES` data component directly from `GearRecalculateEvent.Post`
  (after Silent Gear has already written it) rather than hooking
  `GetPropertyModifiersEvent` - see "What changed after a real build" below
  for why.
- Silent Gear items that reach a finished state WITHOUT ever touching an
  Overgeared anvil (pattern-crafted parts, non-metal assemblies, or any other
  Silent Gear crafting path the pack keeps open) get a fixed default quality
  (config: `defaultUnforgedQuality`, `WELL` unless changed) stamped on first
  recalculation, so the attribute-bonus layer above means something for every
  Silent Gear item, not only forged ones. This never overwrites a real
  anvil-forged roll.
- Late-game non-metal materials still route through the Overgeared anvil (the
  "cold-forging" case) rather than getting the fixed default - Overgeared's
  minigame itself is material-agnostic (it grades the player's execution, not
  the input), so any material this mod adds a forging recipe for gets a real
  player-rolled quality, same as metal tiers.

See `VppIntegration.java`'s class doc for the fully detailed per-hook design
writeup, including confidence levels and exactly what still needs real-build
verification.

## What's verified vs. what still needs an in-game check

This mod now **compiles cleanly and produces a jar** (`./gradlew build`
succeeds end-to-end, including NeoForge/Minecraft dependency resolution,
decompile/patch/recompile, and this mod's own `compileJava` - see "Build
instructions" below). The mod's source was originally authored in a sandbox
with no JDK/network at all, where every class/method signature was guessed
from `strings` output; that sandbox's guesses have since been corrected
against the real, resolved dependency jars using `javap -p -c`. All
`TODO(real-build)` markers have been resolved and removed. What changed:

- `MaterialInstance.fromItem(ItemStack) -> Material` **does not exist**. The
  real API is `MaterialInstance.from(ItemStack) -> MaterialInstance` (nullable),
  which already does the material lookup *and* wraps it - no separate
  `MaterialInstance.of(Material)` call needed. Fixed in
  `AbstractSmithingAnvilBlockEntityMixin`.
- `AbstractSmithingAnvilBlockEntity.craftItem` takes **no parameters** (not
  `craftItem(ServerPlayer)`). The acting player is read off the block
  entity's own `protected Player player` field via a `@Shadow` field instead
  of an injected method parameter. Fixed in the same mixin.
- `GetPropertyModifiersEvent.getPropertyKey()` returns a `PropertyKey<T, V>`
  wrapper, not the raw `GearProperty` - comparing it directly against
  `GearProperties.DURABILITY.get()` is a compile error (`incomparable types`).
  The unwrap is `PropertyKey.property()`.
- **The bigger, runtime-level finding**: even with that unwrap fixed,
  `GetPropertyModifiersEvent.getModifiers()` is **not a mutable list** in the
  case this mod cares about. `javap -p -c` on `CoreGearPart` (the real
  caller) shows the event's `modifiers` list comes from
  `GearProperty.reduce(context, collection)`, whose base implementation is
  `List.copyOf(collection)` (immutable), and `NumberProperty` (the type behind
  `DURABILITY`/`HARVEST_SPEED`) does not override `reduce()`. Calling
  `.add(...)` on that list would have compiled but thrown
  `UnsupportedOperationException` at runtime on the very first Silent Gear
  stat recalculation. `OvergearedSilentGearBridge` no longer hooks this event
  at all - it now rewrites the item's `SgDataComponents.GEAR_PROPERTIES` data
  component directly from `GearRecalculateEvent.Post` (confirmed via
  `javap -p -c` on `GearData` that this event fires *after* that component is
  written), the same "read/replace a data component directly" idiom the
  material-correction mixin already uses. See `OvergearedSilentGearBridge`'s
  class doc for the full bytecode evidence.
- The Modrinth Maven facade indexes Overgeared by its Modrinth
  `version_number` (`1.21.1-1.6.16`), not the bare mod version (`1.6.16`) -
  and `mixinextras-{common,neoforge}`'s real Maven Central group id is
  `io.github.llamalad7`, not `org.spongepowered`. Both fixed in `build.gradle`.

**Boot-verified (2026-07-23, GitHub #67 wiring, real L0 boot with Overgeared +
vppintegration installed in the actual pack):** the mixin applies cleanly
(`vppintegration loaded: Overgeared quality <-> Silent Gear stats bridge
active` in the boot log, no `MixinApplyError`/`MixinTransformerError`), all 6
forging recipes register with zero `Unknown registry key`/parse errors, and
`GearRecalculateEvent.Post` fires without exception. Two real defects this
boot caught (neither visible to `./gradlew build` or static review, both
fixed - see `DECISIONS.md`'s "#67" entry for the full detail):
- `copper_sword_head_silentgear.json`/`iron_sword_head_silentgear.json`
  shipped with `"result": {"id": "silentgear:sword_head"}`, which is not a
  real Silent Gear item id (the part is `silentgear:sword_blade` -
  `pickaxe_head`/`axe_head` were already correct). Both recipes 404'd every
  boot until fixed.
- `OvergearedSilentGearBridge` read `QualityBridgeConfig`'s/Overgeared's
  `ServerConfig`'s `ModConfigSpec` values unconditionally; KubeJS's own
  recipe-manager reload lazily constructs a Silent Gear recipe's result item
  (to test recipe filters) during the same pass that loads server configs,
  which called this event handler before either spec had finished loading
  and crashed that recipe reload. Fixed with a `ModConfigSpec.isLoaded()`
  guard + documented-default fallback.

Still needs a real in-game check (L0 only proves the server boots and the
datapack/mixin load cleanly, not gameplay correctness):

- The corrected material list is visible in the item's tooltip after a real
  anvil forge (mixin logic itself, as opposed to "does it apply", is
  unverified live).
- `GearRecalculateEvent.Post`'s ordering relative to the `GEAR_PROPERTIES`
  write holds for every recalculation path in practice (bytecode-confirmed
  for the direct call path; Silent Gear's traits/enchant hooks could
  theoretically re-trigger recalculation after this listener runs, which
  would just mean the quality bonus gets recomputed on top of a fresh base -
  not obviously wrong, but unverified live).
- `c:melee_weapon_tools` / `c:armors` are tags Silent Gear's items actually
  carry (the attribute-bonus JSON assumes this).
- The example forging recipes for copper/iron sword/pickaxe/axe heads work
  end-to-end in the actual anvil minigame (they now at least load and
  register correctly, per the boot test above).

## Extending to the pack's full material ladder

The shipped `data/overgeared/recipe/forging/*_silentgear.json` files only
cover copper and iron (the two tiers Overgeared already has native
`heated_*_ingot` items + blasting recipes for) across three part types, as a
worked example of the pattern. Vanilla++ has several material tiers beyond
that (steel, and the late-game Allthemodium/Vibranium/Unobtainium chain -
see the parent repo's `DESIGN.md`). Extending coverage is mechanical, no new
design needed:

1. For a material Overgeared doesn't already have a `heated_<material>_ingot`
   item for, add one (a plain `Item` registration + a `minecraft:blasting`
   recipe from the raw ingot, mirroring `heated_iron_ingot_from_blasting_iron_ingot.json`
   in the installed Overgeared jar).
2. Add one `overgeared:forging` recipe per (part type x material) whose
   `key`/`hammering`/`pattern`/`tier`/`category` mirror Overgeared's own
   native recipes for an equivalent tier, and whose `result` is the matching
   Silent Gear part item id (see Silent Gear's own
   `data/silentgear/recipe/gear/*.json` for the full part-item-id list this
   mod's mixin corrects against).

## Build instructions

**Automated (what the pack build actually uses, GitHub #67):**
`python3 scripts/build_local_mods.py` (or just `python3
scripts/resolve_mods.py`, which now calls it first automatically - see that
script's own docstring) stages `libs/silent-gear-*.jar`/`libs/silent-lib-*
.jar` from whatever `pack/mods.lock.json` currently pins for those two slugs
(per this directory's own `libs.json`) and runs `./gradlew build`, from the
parent repo root. This is what CI (`boot.yml`/`mint-release.yml`, both
already set up JDK 21) and any local dev run against.

**Manual**, confirmed working end-to-end (JDK 21, Gradle 8.10, network
access to `services.gradle.org`, `api.modrinth.com`, and `repo1.maven.org`/
`maven.neoforged.net` for the NeoForge/Minecraft/mixinextras dependencies):

```sh
cd mods-src/vppintegration
mkdir -p libs
cp /path/to/silent-gear-1.21.1-neoforge-4.2.1.1.jar libs/
cp /path/to/silent-lib-1.21.1-neoforge-10.6.0.jar libs/
./gradlew build
```

`gradlew`/`gradlew.bat` are committed, but `gradle/wrapper/gradle-wrapper.jar`
(a binary) is gitignored. If it's missing, generate it once with any local
Gradle 8.x install: `gradle wrapper --gradle-version 8.10`, then re-run
`./gradlew build`.

`JAVA_HOME` must point at a JDK 21 (`java.toolchain.languageVersion = 21` in
`build.gradle`). The first build decompiles/patches/recompiles NeoForge
itself (a one-time ~2 minute step per Gradle user-home cache); rebuilds after
that are seconds. The built jar lands at
`build/libs/vppintegration-1.0.0.jar`, which `pack/manifest.json`'s
`vppintegration` entry (`"source": "local"`) now points at - see the parent
repo's `README.md` ("Custom mods" in the repo layout table) and
`scripts/resolve_mods.py`/`scripts/build_local_mods.py` for exactly how that
jar enters the pack build.

## License

MIT - see `LICENSE`. Not affiliated with either Overgeared or Silent Gear;
this is a third-party compatibility bridge distributed independently of both.
