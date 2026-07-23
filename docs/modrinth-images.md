<!--
  Image plan for the Vanilla++ Modrinth project page.

  Nothing here is auto-embedded anywhere; this is a plan + a licensing
  audit for whoever (owner/PM) actually uploads images to the Modrinth
  project. Publishing itself needs the MODRINTH_TOKEN CI secret, same as
  the page body in modrinth-page.md.

  Hard rule followed throughout: never propose an asset whose redistribution
  terms aren't confirmed to permit use on a modpack page. Mod screenshots,
  mod logos, and promo art belong to their respective mod authors and are
  NOT proposed here for that reason, even though they'd be the most
  "obviously relevant" pictures for a page like this.
-->

# Vanilla++ — Modrinth page image plan

No in-game client is available in this environment, so none of the
gameplay screenshots below could actually be captured here. This file is a
shot list for the pack owner (or whoever next has a live client) plus the
licensing basis for the one asset that *was* produced in this pass (the
banner).

## 1. Gallery banner / project icon

**Provided in this PR**: `docs/modrinth-banner.svg`, an original vector
graphic built from scratch for this task — plain geometric shapes and web
system fonts only, no imported artwork, no mod logos, no copied iconography
from Create or any other mod. It reads "VANILLA++" over a simple stylized
gear/cog motif (a generic mechanical shape, not any specific mod's brand
asset) and a tier-ladder motif (a stair-step gradient) to hint at the
progression theme.

- **Licensing basis**: wholly original work authored for this repo as
  part of this task. The pack owner (repo owner) holds full rights to it
  and can use/modify/redistribute it freely on the Modrinth page, GitHub,
  or anywhere else.
- **Recommendation**: use as-is for the project icon/gallery header, or
  treat it as a placeholder and commission/design a proper logo later —
  either is licensing-safe. If the owner wants a more polished banner,
  the safest path is still an original commissioned piece, or the owner's
  own design work — not adapting any existing mod's promotional art.

## 2. Gameplay screenshots (recommend: owner-captured, in-game)

These need a live client and a populated world, neither of which exists in
this sandbox. **Recommendation: the pack owner (or a player with a
progressed save) captures these themselves** — screenshots of your own
gameplay session are yours to use on your own project page with no
licensing question at all. Suggested shot list, one per major feature
area so the gallery mirrors the page's own feature grouping:

1. **Tier ladder / Create automation** — a working Create contraption
   mid-tier (e.g. a Brass Age Mechanical Arm/Deployer setup feeding a
   storage network), ideally with the tier-unlock toast/HUD element
   visible if one exists.
2. **Blacksmithing** — the Silent Gear Gear Workbench UI mid-assembly, or
   a freshly forged tool next to its blueprint/parts.
3. **Storage progression** — a Refined Storage Grid/Controller setup (late
   game) — optionally paired with an early Tom's Storage terminal shot to
   show the contrast the page's "storage scales with you" section
   describes.
4. **Skill tree** — the Puffish Skills UI open on one of the 23 categories,
   showing node buffs.
5. **Economy/marketplace** — a Create: Numismatics Vendor block UI, or the
   Create: Marketplace board showing multiple player shops.
6. **Quests** — the FTB Quests chapter-select screen showing the per-tier
   quest chapters.
7. **Combat** — an Epic Fight weapon moveset in action (any of the five
   new weapon classes), or an Ars Nouveau spell being cast.
8. **World/exploration** — a notable generated structure, or the
   four-tier jetpack/creative-flight capstone in use.
9. **Space travel (endgame)** — a Stellaris rocket launch or a shot from
   one of the additional planet tiers (Moon/Mars/etc.), since this is the
   pack's stated ultimate-goal system.

None of these are provided as files in this PR — they require an actual
play session. Do not substitute a screenshot from Create's, Silent Gear's,
Epic Fight's, Ars Nouveau's, Refined Storage's, or any other mod's own
Modrinth/CurseForge page — those are the respective mod authors' assets,
not licensed for reuse on a different project's page.

## 3. Things explicitly NOT proposed, and why

- **Mod logos/icons** (Create, Silent Gear, Epic Fight, Ars Nouveau,
  Refined Storage, Stellaris, etc.) — each belongs to its own mod author;
  no blanket redistribution permission is confirmed for use on a
  third-party modpack's promotional page.
- **Screenshots scraped from mod wiki/Modrinth pages** — same issue: these
  are the mod authors' own promotional material, not this project's to
  redistribute.
- **Stock "Minecraft-style" art from generic asset sites** — skipped
  rather than risk citing a license that turns out not to actually permit
  commercial/redistributable use; if the owner wants filler art beyond the
  banner above, the safest source is still their own screenshots or a
  confirmed CC0 asset with the exact license page cited at time of use.

If the owner (or a later agent with client access) captures real
screenshots, add them under this project's `docs/` (or wherever the repo
keeps binary assets) and update this file to record, per image, exactly
where it came from — that provenance note is what makes each future image
safe to keep using.
