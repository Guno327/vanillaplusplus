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
  material-detection API (`MaterialInstance.fromItem`), then asks Silent Gear
  to recompute stats (`GearData.recalculateGearData`) - not a guess at the
  private codec.
- Silent Gear's own non-vanilla-attribute stats (durability, harvest speed -
  its own `GearPropertyMap`/`GetPropertyModifiersEvent` system, separate from
  vanilla Attributes) get a quality-scaled bonus from
  `dev.vanillaplusplus.vppintegration.quality.OvergearedSilentGearBridge`,
  reusing Overgeared's own per-quality config bonus values
  (`ServerConfig.*_DURABILITY_BONUS` / `*_MINING_SPEED_BONUS`) for symmetry
  with Overgeared's native items.
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

## What's verified vs. what needs a real build

This mod's source was authored in a sandbox with **no JDK at all** (not just
no network) - `javap`/`cfr`/`fernflower` were unavailable, so every class
name, field, and method signature cited above and in code comments was
confirmed via `strings` against the actual installed jars
(`silent-gear-1.21.1-neoforge-4.2.1.1.jar`,
`silent-lib-1.21.1-neoforge-10.6.0.jar`, and a downloaded
`overgeared-1.21.1-1.6.16.jar`) - real class/method *names* are confirmed,
but exact bytecode descriptors (parameter types, generic bounds) could not be.
Every place this matters is marked `TODO(real-build)` in the source. A real
build environment must:

1. Have a JDK 21 and run `./gradlew build` (needs network access to
   `api.modrinth.com/maven` for the Overgeared compile dependency, and the two
   Silent Gear jars copied into `libs/` - see "Build instructions" below).
2. Run `javap -p` (or decompile with a real tool) against
   `AbstractSmithingAnvilBlockEntity.craftItem`, `ForgingQualityHelper.
   applyForgingQuality`, `MaterialInstance.fromItem`/`.of`,
   `GetPropertyModifiersEvent`, and `GearProperties.DURABILITY`/
   `HARVEST_SPEED`'s field types, to confirm every signature this mod's
   mixin/event listeners assume.
3. Boot a real client+server with all three mods to verify:
   - The mixin actually applies (no `MixinApplyError`) and the corrected
     material list is visible in the item's tooltip.
   - `GetPropertyModifiersEvent` actually fires per-part with a way to
     recover the parent gear ItemStack's quality (flagged as the least
     certain hook in `OvergearedSilentGearBridge`'s class doc - if the event
     doesn't carry that context, the fallback is capturing quality via
     `GearRecalculateEvent.Pre` into a thread-local, which is what this mod
     already does, but the *correctness* of that thread-local approach under
     Silent Gear's real threading/recursion behavior needs a live check).
   - `c:melee_weapon_tools` / `c:armors` are tags Silent Gear's items
     actually carry (the attribute-bonus JSON assumes this).
   - The example forging recipes for copper/iron sword/pickaxe/axe heads
     work end-to-end in the actual anvil minigame.

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

This sandbox had **no JDK/Gradle installed at all**, so `gradle/wrapper/
gradle-wrapper.jar` (a binary) could not be generated here - only
`gradle-wrapper.properties` (pinning Gradle 8.10) is committed. A real build
environment must run `gradle wrapper` once with any local Gradle install to
produce the jar, or just use a system Gradle directly instead of `./gradlew`:

```sh
cd mods-src/vppintegration
mkdir -p libs
cp /path/to/silent-gear-1.21.1-neoforge-4.2.1.1.jar libs/
cp /path/to/silent-lib-1.21.1-neoforge-10.6.0.jar libs/
gradle wrapper        # one-time, generates gradle-wrapper.jar
./gradlew build        # or: gradle build
```

The built jar lands at `build/libs/vppintegration-1.0.0.jar`. See the parent
repo's `README.md` ("Custom mods" in the repo layout table) and
`scripts/resolve_mods.py`/`pack/manifest.json` for how that jar is wired into
the Vanilla++ pack build (`"source": "local"` manifest entries).

## License

MIT - see `LICENSE`. Not affiliated with either Overgeared or Silent Gear;
this is a third-party compatibility bridge distributed independently of both.
