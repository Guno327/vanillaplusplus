# Third-party mod credits and licenses

This repository's own content (KubeJS scripts, configs, build/CI scripts,
docs, pack manifests/lockfiles, progression data, and the custom mods under
`mods-src/`) is MIT-licensed -- see [LICENSE](LICENSE).

**The 113 third-party Minecraft mods this pack installs are each under their
own license, NOT this repository's MIT license.** A modpack is a legal
aggregation of independently-licensed works; installing/referencing a mod
here does not relicense it. This file credits every mod and states its
license so operators/redistributors know what applies to what.

Generated from the Modrinth API (`GET /v2/projects?ids=[...]` +
`GET /v2/teams?ids=[...]`, keyed off each entry's `project_id` in
[`pack/mods.lock.json`](pack/mods.lock.json)) plus manual lookup for the two
CurseForge-sourced mods (`ato`, `allthemodium`, which have no Modrinth page).
Regenerate any time the same way if mods are added/removed/updated.

## License summary (113 mods)

| Bucket | Count | Redistribution note |
|---|---|---|
| Permissive (MIT / Apache-2.0 / Unlicense / CC0-1.0) | 44 | Free to bundle/redistribute. |
| Weak-copyleft (LGPL-2.1/3.0, MPL-2.0) | 30 | Redistribution allowed; ship license text with the jar. Doesn't touch this repo's own MIT license. |
| Strong-copyleft (GPL-3.0) | 6 | Redistribution allowed. This pack's own custom Java (`vppintegration`/`vppquests`) derives from none of these -- verified by dependency review -- so no copyleft obligation attaches to this repo's code. |
| **CC-BY-NC-SA (NonCommercial)** | **4** (`extradelight`, `jade`, `patchouli`, `stellaris`) | Non-commercial use only. See the Modrinth-Rewards research determination below. |
| ARR / custom "LicenseRef-*" (all-rights-reserved or a bespoke permission page) | 27 | Redistribution NOT clearly granted -- this is the reason the server distribution no longer bundles third-party jars (see "Distribution model" below). |
| CurseForge-sourced, no Modrinth page (`ato`, `allthemodium`) | 2 | No LICENSE file in either mod's GitHub repo -- treated as all-rights-reserved, same distribution constraint as the ARR bucket above. |

## Distribution model

Per GitHub #141: the released **server bundle does not ship any of these 113
jars**. It ships an install script
(`scripts/install_mods.py` / the copy embedded at the root of the release
zip) plus a URL+hash manifest; the script downloads each jar straight from
its own origin (Modrinth CDN or CurseForge CDN) and verifies it against the
sha1/sha512 pinned in `pack/mods.lock.json` before use. This mirrors how the
client `.mrpack` has always worked (Modrinth's own launcher format installs
mods by URL, never by bundling). This repo's own custom mods (`local_path`
entries in `pack/manifest.json` -- `vppintegration` as of GitHub #67/#124,
this pack's own Overgeared x Silent Gear quality bridge) remain shipped
directly inside the server zip's `mods/`, since we own their copyright (MIT,
same as this repo -- see `mods-src/vppintegration/LICENSE`). They are NOT
listed in the table below (that table is third-party mods only); Overgeared
itself, the separate Modrinth mod `vppintegration` bridges to, IS listed
below since it's third-party.

## CC-BY-NC-SA vs. Modrinth Rewards -- determination

**Determination: not a clear violation** (full reasoning in
[DECISIONS.md](DECISIONS.md)'s "GitHub #141" entry). In short: this pack is
a free download with no paywall; the only money nearby is Modrinth's own
Rewards Program (ad revenue Modrinth itself sells/serves on its own site).
Modrinth's own published mechanics (modrinth.com/legal/cmp-info, the
"Creators can now make money on Modrinth!" announcement) state that for
modpacks, revenue is split **80% to the pack's Modrinth dependencies and
20% to the modpack author** -- meaning most of whatever Rewards this pack's
inclusion of `jade`/`patchouli`/`stellaris`/`extradelight` generates flows
to *those mods' own authors*, applied uniformly with no license-based
carve-out documented anywhere in Modrinth's terms. `jade`/`patchouli` are
two of the most widely-depended-upon mods on the whole platform, included
in an enormous number of monetized packs industry-wide, with no known
enforcement precedent. No mod swap or follow-up issue is being filed;
this sub-task is closed with this written determination. If the owner
wants zero residual risk regardless, they can request the swap later --
`jade`/`patchouli` have many dependents in this pack (e.g. the Apotheosis
chain requires `patchouli`), so a preemptive swap has real cascade cost
against a risk this determination finds weak.

## Full mod list

| Mod | Author | License | Source |
|---|---|---|---|
| [Advanced Loot Info (ALI)](https://modrinth.com/mod/advanced-loot-info) | lalis.jan | [MIT](https://github.com/yanny7/AdvancedLootInfo/blob/master/LICENSE) | Modrinth |
| [Allthemodium](https://www.curseforge.com/minecraft/mc-mods/allthemodium) | AllTheMods / Shadows_of_Fire (ATM team) | [ARR (no LICENSE file)](https://github.com/AllTheMods/AllTheModium) | CurseForge |
| [AllTheOres](https://www.curseforge.com/minecraft/mc-mods/ato) | AllTheMods / Shadows_of_Fire (ATM team) | [ARR (no LICENSE file)](https://github.com/AllTheMods/AllTheOres) | CurseForge |
| [Apotheosis](https://modrinth.com/mod/apotheosis) | Shadows-of-Fire | MIT | Modrinth |
| [Apothic Attributes](https://modrinth.com/mod/apothic-attributes) | Shadows-of-Fire | MIT | Modrinth |
| [Apothic-Enchanting](https://modrinth.com/mod/apothic-enchanting) | Shadows-of-Fire | MIT | Modrinth |
| [Apothic-Spawners](https://modrinth.com/mod/apothic-spawners) | Shadows-of-Fire | MIT | Modrinth |
| [AppleSkin](https://modrinth.com/mod/appleskin) | squeek502 | Unlicense | Modrinth |
| [Architectury API](https://modrinth.com/mod/architectury-api) | MaxNeedsSnacks | LGPL-3.0-only | Modrinth |
| [Ars Nouveau](https://modrinth.com/mod/ars-nouveau) | baileyholl | GPL-3.0-only | Modrinth |
| [Artifacts](https://modrinth.com/mod/artifacts) | ochotonida | MIT | Modrinth |
| [BaguetteLib](https://modrinth.com/mod/baguettelib) | Leclowndu93150 | MIT | Modrinth |
| [Balm](https://modrinth.com/mod/balm) | BlayTheNinth | [LicenseRef-All-Rights-Reserved](https://mods.twelveiterations.com/permissions) | Modrinth |
| [Bookshelf](https://modrinth.com/mod/bookshelf-lib) | Darkhax | LGPL-2.1-only | Modrinth |
| [Born in Chaos](https://modrinth.com/mod/borninchaos) | Mongoose_artist | LicenseRef-All-Rights-Reserved | Modrinth |
| [Building Wands](https://modrinth.com/mod/building-wands) | nicguzzo | Apache-2.0 | Modrinth |
| [Client Sort](https://modrinth.com/mod/clientsort) | NotRyken | Apache-2.0 | Modrinth |
| [Cloth Config API](https://modrinth.com/mod/cloth-config) | shedaniel | LGPL-3.0-only | Modrinth |
| [Clumps](https://modrinth.com/mod/clumps) | jaredlll08 | MIT | Modrinth |
| [Concurrent Chunk Management Engine (NeoForge)](https://modrinth.com/mod/c2me-neoforge) | ishland | MIT | Modrinth |
| [Controlling](https://modrinth.com/mod/controlling) | jaredlll08 | MIT | Modrinth |
| [Create](https://modrinth.com/mod/create) | simibubi | [LicenseRef-Create-Mod-License](https://github.com/Creators-of-Create/Create/blob/HEAD/LICENSE.md) | Modrinth |
| [Create Aeronautics](https://modrinth.com/mod/create-aeronautics) | Creators-of-Aeronautics (org) | [LicenseRef-Simulated-Project-License](https://github.com/Creators-of-Aeronautics/Simulated-Project/blob/main/LICENSE.md) | Modrinth |
| [Create Crafts & Additions](https://modrinth.com/mod/createaddition) | mrh0 | [MIT](https://tldrlegal.com/license/mit-license) | Modrinth |
| [Create Ore Excavation](https://modrinth.com/mod/create-ore-excavation) | tom5454 | MIT | Modrinth |
| [Create Stuff & Netherite Additions](https://modrinth.com/mod/create-netherite-additions) | fabenet | LicenseRef-All-Rights-Reserved | Modrinth |
| [Create Stuff 'N Additions](https://modrinth.com/mod/create-stuff-additions) | furti-two | LicenseRef-All-Rights-Reserved | Modrinth |
| [Create: Central Kitchen](https://modrinth.com/mod/create-central-kitchen) | MarbleGateKeeper | LGPL-3.0-or-later | Modrinth |
| [Create: Dragons Plus](https://modrinth.com/mod/create-dragons-plus) | MarbleGateKeeper | LGPL-3.0-or-later | Modrinth |
| [Create: Marketplace](https://modrinth.com/mod/create-marketplace) | MakotoPD | [GPL-3.0-only](https://raw.githubusercontent.com/MakotoPD/CreateMarketplace/refs/heads/main/LICENSE) | Modrinth |
| [Create: Numismatics](https://modrinth.com/mod/numismatics) | IThundxr | LGPL-3.0-only | Modrinth |
| [Create: Power Loader](https://modrinth.com/mod/create-power-loader) | Lysine | [MIT](https://github.com/hlysine/create_power_loader/blob/main/LICENSE) | Modrinth |
| [Create: TFMG - Stellaris Compat](https://modrinth.com/mod/tfmg-stellaris-compat) | ptr47 | MIT | Modrinth |
| [Create: The Factory Must Grow](https://modrinth.com/mod/create-tfmg) | drmangotea | MIT | Modrinth |
| [CreativeCore](https://modrinth.com/mod/creativecore) | creativemd | LGPL-3.0-only | Modrinth |
| [Creeper Overhaul](https://modrinth.com/mod/creeper-overhaul) | Joo5h | LicenseRef-All-Rights-Reserved | Modrinth |
| [Curios API](https://modrinth.com/mod/curios) | TheIllusiveC4 | LGPL-3.0-or-later | Modrinth |
| [Dungeons and Taverns](https://modrinth.com/mod/dungeons-and-taverns) | NovaWostra | LicenseRef-All-Rights-Reserved | Modrinth |
| [Dynamic FPS](https://modrinth.com/mod/dynamic-fps) | juliand665 | MIT | Modrinth |
| [Enchantment Descriptions](https://modrinth.com/mod/enchantment-descriptions) | Darkhax | LGPL-2.1-only | Modrinth |
| [End's Delight](https://modrinth.com/mod/ends-delight) | FoggyHillside | MIT | Modrinth |
| [Entity Culling](https://modrinth.com/mod/entityculling) | tr7zw | [LicenseRef-tr7zw-Protective-License](https://github.com/tr7zw/EntityCulling/blob/1.18/LICENSE-EntityCulling) | Modrinth |
| [Epic Fight](https://modrinth.com/mod/epic-fight) | MetalKnight56 | GPL-3.0-or-later | Modrinth |
| [ExtraDelight](https://modrinth.com/mod/extradelight) | Lance5057 | CC-BY-NC-SA-4.0 | Modrinth |
| [Farmer's Delight](https://modrinth.com/mod/farmers-delight) | vectorwing | MIT | Modrinth |
| [FasterLadderClimbing](https://modrinth.com/mod/fasterladderclimbing) | Nikrecs | MIT | Modrinth |
| [FerriteCore](https://modrinth.com/mod/ferrite-core) | malte0811 | MIT | Modrinth |
| [Geckolib](https://modrinth.com/mod/geckolib) | Gecko | MIT | Modrinth |
| [GraveStone Mod](https://modrinth.com/mod/gravestone-mod) | henkelmax | LicenseRef-All-Rights-Reserved | Modrinth |
| [Gravestone x Curios API Compat](https://modrinth.com/mod/gravestone-x-curios-api-compat) | Leclowndu93150 | MIT | Modrinth |
| [ImmediatelyFast](https://modrinth.com/mod/immediatelyfast) | RaphiMC | LGPL-3.0-or-later | Modrinth |
| [Iris & Oculus Flywheel Compat](https://modrinth.com/mod/iris-flw-compat) | leon-o | CC0-1.0 | Modrinth |
| [Iris Shaders](https://modrinth.com/mod/iris) | coderbot | LGPL-3.0-only | Modrinth |
| [Jade Addons (Neo/Forge)](https://modrinth.com/mod/jade-addons-forge) | Snownee | LicenseRef-All-Rights-Reserved | Modrinth |
| [Jade 🔍](https://modrinth.com/mod/jade) | Snownee | CC-BY-NC-SA-4.0 | Modrinth |
| [JEI / REI / EMI WorldGen](https://modrinth.com/mod/jei-worldgen) | Larsens-Mods (org) | GPL-3.0-only | Modrinth |
| [Just Enough Breeding (JEBr)](https://modrinth.com/mod/justenoughbreeding) | Christofmeg | MIT | Modrinth |
| [Just Enough Effect Descriptions (JEED)](https://modrinth.com/mod/just-enough-effect-descriptions-jeed) | MehVahdJukaar | LicenseRef-All-Rights-Reserved | Modrinth |
| [Just Enough Items (JEI)](https://modrinth.com/mod/jei) | mezz | MIT | Modrinth |
| [Just Enough Professions (JEP)](https://modrinth.com/mod/just-enough-professions-jep) | Mrbysco | MIT | Modrinth |
| [Just Enough Resources (JER)](https://modrinth.com/mod/just-enough-resources-jer) | way2muchnoise | [LicenseRef-Dont-Be-a-Jerk](https://github.com/way2muchnoise/JustEnoughResources/blob/master/LICENSE.md) | Modrinth |
| [Krypton Reno](https://modrinth.com/mod/krypton-fnp) | 4x | LGPL-3.0-only | Modrinth |
| [KubeJS](https://modrinth.com/mod/kubejs) | Lat | LGPL-3.0-only | Modrinth |
| [Lithostitched](https://modrinth.com/mod/lithostitched) | Apollo | MIT | Modrinth |
| [Lootr](https://modrinth.com/mod/lootr) | noobanidus | MIT | Modrinth |
| [ModernFix](https://modrinth.com/mod/modernfix) | embeddedt | LGPL-3.0-only | Modrinth |
| [More Culling](https://modrinth.com/mod/moreculling) | FX | GPL-3.0-only | Modrinth |
| [Naturalist](https://modrinth.com/mod/naturalist) | crispytwig | [LicenseRef-Custom](https://github.com/starfish-studios/Naturalist/blob/1.19/LICENSE) | Modrinth |
| [Noisiumed](https://modrinth.com/mod/noisiumed) | imbavirus | [GPL-3.0-only](https://raw.githubusercontent.com/imbavirus/noisiumed/refs/heads/1.21-1.21.1/LICENSE) | Modrinth |
| [Open Parties and Claims](https://modrinth.com/mod/open-parties-and-claims) | thexaero | LGPL-3.0-only | Modrinth |
| [Overgeared](https://modrinth.com/mod/overgeared) | StirDrem | MIT | Modrinth |
| [Patchouli](https://modrinth.com/mod/patchouli) | Vazkii | CC-BY-NC-SA-3.0 | Modrinth |
| [Placebo](https://modrinth.com/mod/placebo) | Shadows-of-Fire | MIT | Modrinth |
| [Potentials](https://modrinth.com/mod/potentials) | Fej1Fun | MIT | Modrinth |
| [Prickle](https://modrinth.com/mod/prickle) | Darkhax | LGPL-2.1-only | Modrinth |
| [Pufferfish's Attributes](https://modrinth.com/mod/attributes) | Pufferfish | LGPL-3.0-only | Modrinth |
| [Pufferfish's Skills](https://modrinth.com/mod/skills) | Pufferfish | [LicenseRef-Custom](https://github.com/pufmat/skillsmod/wiki/License) | Modrinth |
| [Refined Storage](https://modrinth.com/mod/refined-storage) | refinedmods (org) | MIT | Modrinth |
| [Resourceful Config](https://modrinth.com/mod/resourceful-config) | epic_oreo | MIT | Modrinth |
| [Resourceful Lib](https://modrinth.com/mod/resourceful-lib) | ThatGravyBoat | MIT | Modrinth |
| [Rhino](https://modrinth.com/mod/rhino) | Lat | MPL-2.0 | Modrinth |
| [Sable](https://modrinth.com/mod/sable) | ryanhcode | [LicenseRef-PolyForm-Shield-License-1.0.0](https://github.com/ryanhcode/sable/blob/main/LICENSE.md) | Modrinth |
| [Searchables](https://modrinth.com/mod/searchables) | jaredlll08 | MIT | Modrinth |
| [Silent Gear](https://modrinth.com/mod/silent-gear) | SilentChaos512 | MIT | Modrinth |
| [Silent Lib](https://modrinth.com/mod/silent-lib) | SilentChaos512 | MIT | Modrinth |
| [Simply Harvesting](https://modrinth.com/mod/simply-harvesting) | MelanX | Apache-2.0 | Modrinth |
| [Sodium](https://modrinth.com/mod/sodium) | jellysquid3 | [LicenseRef-Polyform-Shield-1.0.0](https://github.com/CaffeineMC/sodium/blob/dev/LICENSE.md) | Modrinth |
| [Sophisticated Backpacks](https://modrinth.com/mod/sophisticated-backpacks) | P3pp3rF1y | LicenseRef-All-Rights-Reserved | Modrinth |
| [Sophisticated Core](https://modrinth.com/mod/sophisticated-core) | P3pp3rF1y | LicenseRef-All-Rights-Reserved | Modrinth |
| [Sophisticated Storage](https://modrinth.com/mod/sophisticated-storage) | P3pp3rF1y | LicenseRef-All-Rights-Reserved | Modrinth |
| [Spice of Life Onion](https://modrinth.com/mod/spice-of-life-onion) | creativemd | LGPL-3.0-only | Modrinth |
| [Stellaris](https://modrinth.com/mod/stellaris) | Okamiz | CC-BY-NC-SA-4.0 | Modrinth |
| [Structory](https://modrinth.com/mod/structory) | catter1 | [LicenseRef-Stardust-Labs-License](https://github.com/Stardust-Labs-MC/license/blob/main/license.txt) | Modrinth |
| [TerraBlender](https://modrinth.com/mod/terrablender) | Adubbz | [LGPL-3.0-only](https://github.com/Glitchfiend/TerraBlender/blob/TB-1.19.3-2.1.x/LICENSE) | Modrinth |
| [Terralith](https://modrinth.com/mod/terralith) | Starmute | [LicenseRef-Stardust-Labs-License](https://github.com/Stardust-Labs-MC/license/blob/main/license.txt) | Modrinth |
| [Time in a bottle](https://modrinth.com/mod/time-in-a-bottle-universal) | MangoRage | MIT | Modrinth |
| [Time in a Bottle Fix - Tiab Fix](https://modrinth.com/mod/time-in-a-bottle-fix-tiab-fix) | zulussu | MIT | Modrinth |
| [Tom's Simple Storage Mod](https://modrinth.com/mod/toms-storage) | tom5454 | MIT | Modrinth |
| [TrashSlot](https://modrinth.com/mod/trashslot) | BlayTheNinth | [LicenseRef-All-Rights-Reserved](https://mods.twelveiterations.com/permissions) | Modrinth |
| [Waystones](https://modrinth.com/mod/waystones) | BlayTheNinth | [LicenseRef-All-Rights-Reserved](https://mods.twelveiterations.com/permissions) | Modrinth |
| [When Dungeons Arise](https://modrinth.com/mod/when-dungeons-arise) | aureljz | LicenseRef-All-Rights-Reserved | Modrinth |
| [Xaero's Minimap](https://modrinth.com/mod/xaeros-minimap) | thexaero | LicenseRef-All-Rights-Reserved | Modrinth |
| [Xaero's World Map](https://modrinth.com/mod/xaeros-world-map) | thexaero | LicenseRef-All-Rights-Reserved | Modrinth |
| [YUNG's API](https://modrinth.com/mod/yungs-api) | YUNGNICKYOUNG | LGPL-3.0-only | Modrinth |
| [YUNG's Better Desert Temples](https://modrinth.com/mod/yungs-better-desert-temples) | TeraBuildsStuff | LGPL-3.0-only | Modrinth |
| [YUNG's Better Dungeons](https://modrinth.com/mod/yungs-better-dungeons) | Acarii | LGPL-3.0-only | Modrinth |
| [YUNG's Better End Island](https://modrinth.com/mod/yungs-better-end-island) | YUNGNICKYOUNG | LGPL-3.0-only | Modrinth |
| [YUNG's Better Jungle Temples](https://modrinth.com/mod/yungs-better-jungle-temples) | YUNGNICKYOUNG | LGPL-3.0-only | Modrinth |
| [YUNG's Better Mineshafts](https://modrinth.com/mod/yungs-better-mineshafts) | YUNGNICKYOUNG | LGPL-3.0-only | Modrinth |
| [YUNG's Better Nether Fortresses](https://modrinth.com/mod/yungs-better-nether-fortresses) | YUNGNICKYOUNG | LGPL-3.0-only | Modrinth |
| [YUNG's Better Ocean Monuments](https://modrinth.com/mod/yungs-better-ocean-monuments) | TeraBuildsStuff | LGPL-3.0-only | Modrinth |
| [YUNG's Better Strongholds](https://modrinth.com/mod/yungs-better-strongholds) | YUNGNICKYOUNG | LGPL-3.0-only | Modrinth |
| [YUNG's Better Witch Huts](https://modrinth.com/mod/yungs-better-witch-huts) | YUNGNICKYOUNG | LGPL-3.0-only | Modrinth |
