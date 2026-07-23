# Vanilla++ Fixes (`vppfixes`)

A tiny, Mixin-only "pack fixes" mod for the Vanilla++ modpack: a home for hand-rolled
correctness fixes to third-party mods that can only be expressed as bytecode (a Mixin),
not as a config toggle or a datapack override. It is an owner-approved custom mod (an
exception to the pack's No-New-Mods rule), tracked here under `mods-src/` alongside
`vppintegration` and `vppquests`. This is the pack's third custom mod.

## Fix #1 — GitHub #143: Ars Nouveau entity-data `ConcurrentModificationException`

### Symptom
On the live v0.5.2 server, clients were regularly booted with a client-side
"Internal Exception". Server log root cause:

```
[Netty Epoll Server IO/ERROR] PacketEncoder: Error sending packet clientbound/minecraft:set_entity_data
io.netty.handler.codec.EncoderException: Failed to encode packet 'clientbound/minecraft:set_entity_data'
  ... com.mojang.serialization.codecs.ListCodec.encode ...
  ... net.minecraft.network.syncher.SynchedEntityData$DataValue.write
Caused by: java.util.ConcurrentModificationException
  at java.util.ArrayList$Itr.checkForComodification
```

### Root cause
The crash goes entirely through Mojang DFU codec frames
(`RecordCodecBuilder` → `OptionalFieldCodec` → `ListCodec`, under a
`Codec.recursive`/`EitherCodec`), which only happens for a **Codec-backed**
`EntityDataSerializer`. A bytecode scan of all 113 pack mods found exactly one that
registers such a serializer with a recursive/list codec: **Ars Nouveau**.

Ars registers `ars_nouveau:spell_resolver` via
`EntityDataSerializer.forValueType(SpellResolver.STREAM)`. `forValueType`'s `copy(T)`
is the **identity** function — it is intended for immutable value types. But Ars stores
a **live, mutable** `SpellResolver` object graph
(`Spell` → recipe `List` + `Optional<TimelineMap>` particle timeline, the recursive
codec) as `SynchedEntityData` on `EntityProjectileSpell` and `EntitySpellArrow`.
Because `copy()` is identity, the value the entity tracker packs is the *same instance*
the server tick thread keeps mutating during spell resolution. The tracker then
serializes that live graph on the Netty IO thread (`DataValue.write`), so a main-thread
list mutation races the IO-thread `ListCodec.encode` iteration → CME → the entity-data
packet fails to encode → the tracking client is disconnected. Spell arrows persist stuck
in the ground, so the race recurs periodically (matching the "regularly booted" report).

Neither a config toggle (no Ars config gates this sync) nor a version bump (5.12.1 is
already the newest 1.21.1 build; particle timelines are a recent feature with no upstream
CME fix) can address it, and Ars is a load-bearing archetype mod that cannot be removed —
hence a targeted Mixin.

### The fix
`dev.vanillaplusplus.vppfixes.mixin.SynchedEntityDataMixin` post-processes the return
value of vanilla `SynchedEntityData#packDirty` and `#getNonDefaultValues`. Both build the
outgoing `List<DataValue<?>>` **on the server tick thread** (called from
`ServerEntity#sendChanges`/`#sendPairingData`); the packet is only *encoded* later, on the
IO thread. For any `DataValue` whose serializer registry-id is in the targeted set
(currently just `ars_nouveau:spell_resolver`), we replace it with a genuine **deep copy**
produced by round-tripping the value through the serializer's own `StreamCodec` on the
tick thread. The IO thread then only ever encodes an immutable, freshly-decoded object that
nothing else references or mutates — CME becomes impossible for that value.

Why it closes the race: the offending mutation is on the tick thread, and now so is the
copy, so the two cannot interleave (same thread); the object handed to the packet is owned
by nobody else. See `SynchedDataSnapshots` for the full rationale.

Design properties:
- **No compile-time dependency on Ars Nouveau** — the target is vanilla
  `SynchedEntityData`, matched by the serializer's registry-id *string*. If Ars is absent
  the mixin is a harmless no-op.
- **Pass-through by default** — every non-targeted entity-data value (the overwhelming
  majority) is returned by reference after one cheap registry-key lookup, so normal entity
  sync is untouched.
- **Degrades gracefully** — if the current server/registry is unavailable or the round-trip
  throws, the original value is returned unchanged (status quo) and the failure is logged
  once, never thrown onto the tick thread.
- **Both physical sides** — not restricted to the dedicated server, so single-player
  (integrated server inside the client jar) is guarded too.

Future pack fixes of the same shape can be added by extending
`SynchedDataSnapshots.TARGET_SERIALIZER_IDS`.

## Build instructions

Standard NeoForge `moddev` build (same toolchain as `vppintegration`):

```bash
cd mods-src/vppfixes
# one-time, if gradle/wrapper/gradle-wrapper.jar is missing:
#   gradle wrapper
./gradlew build
# -> build/libs/vppfixes-1.0.0.jar
```

The jar this pack pins (`pack/mods.lock.json`, `source: "local"`) is the output of that
build. After rebuilding, if the jar hash changes, re-run `scripts/resolve_mods.py` (or hand-
update the lock `hashes`/`filesize`) so `pack/mods.lock.json` matches. No third-party mod
jars are needed on the compile classpath — the mixin references only vanilla + NeoForge.
