# Vanilla++ Fixes (`vppfixes`)

A tiny, Mixin-only "pack fixes" mod for the Vanilla++ modpack: a home for hand-rolled
correctness fixes to third-party mods that can only be expressed as bytecode (a Mixin),
not as a config toggle or a datapack override. It is an owner-approved custom mod (an
exception to the pack's No-New-Mods rule), tracked here under `mods-src/` alongside
`vppintegration` and `vppquests`. This is the pack's third custom mod.

## Fix #1 — GitHub #143: custom-name `Component` entity-data `ConcurrentModificationException`

### Symptom
On the live server, clients were regularly booted with a client-side "Internal Exception".
Server log root cause:

```
[Netty Epoll Server IO/ERROR] PacketEncoder: Error sending packet clientbound/minecraft:set_entity_data
io.netty.handler.codec.EncoderException: Failed to encode packet 'clientbound/minecraft:set_entity_data'
  ... com.mojang.serialization.codecs.ListCodec.encode ...
  ... net.minecraft.network.codec.ByteBufCodecs$19/$20.encode
  ... net.minecraft.network.syncher.SynchedEntityData$DataValue.write
Caused by: java.util.ConcurrentModificationException
  at java.util.ArrayList$Itr.checkForComodification
```

### Root cause
The crash runs entirely through Mojang DFU codec frames
(`Codec.recursive` → `EitherCodec` → `RecordCodecBuilder` → `OptionalFieldCodec` →
`ListCodec`, wrapped in `ByteBufCodecs.fromCodec(...).optional()`). That is the exact
signature of **`ComponentSerialization.CODEC`** — a text `Component` (string-or-list-or-record
`Either`, recursive for nested components, with an optional `siblings` `List`). It is used by
the vanilla `EntityDataSerializers.OPTIONAL_COMPONENT` serializer, i.e. an entity's
**custom name** (`Entity.DATA_CUSTOM_NAME`).

`OPTIONAL_COMPONENT` is a `forValueType` serializer whose `copy(T)` is the **identity**
function — safe only because vanilla treats `Component`s as immutable. When a mod hands the
entity a **live, mutated** `MutableComponent` as its custom name and keeps appending to that
component's `siblings` `ArrayList` on the server tick thread, the entity tracker packs the
*same instance* and serializes it on the Netty IO thread (`DataValue.write`). The tick-thread
list mutation races the IO-thread `ListCodec.encode` iteration → CME → the entity-data packet
fails to encode → the tracking client is disconnected. Dedicated-server only: the integrated
server encodes on the server thread, so there is no race.

The underlying offender is an upstream mod handing a live, per-tick-mutated component to
`setCustomName`; the mixin fixes it mod-agnostically at the vanilla choke point.

> **Correction to the original v0.5.3 diagnosis.** v0.5.3 guessed Ars Nouveau's
> `ars_nouveau:spell_resolver` and matched serializers by registry-id string. That was a
> *double* no-op: (1) `spell_resolver` uses a hand-written `StreamCodec` and cannot produce
> the DFU `ListCodec` frames above, and (2) **vanilla serializers are not registered in
> `NeoForgeRegistries.ENTITY_DATA_SERIALIZERS`** (only modded ones are), so they have no
> `ResourceLocation` key and an id-string match can never fire against them. Both were
> confirmed by reproducing the crash on the L3 client-join test (RED→GREEN below).

### The fix
`dev.vanillaplusplus.vppfixes.mixin.SynchedEntityDataMixin` post-processes the return value
of vanilla `SynchedEntityData#packDirty` and `#getNonDefaultValues`. Both build the outgoing
`List<DataValue<?>>` **on the server tick thread** (called from
`ServerEntity#sendChanges`/`#sendPairingData`); the packet is only *encoded* later, on the
IO thread. For any `DataValue` whose serializer **is** `EntityDataSerializers.COMPONENT` or
`OPTIONAL_COMPONENT` (matched by reference identity — see the note above on why id-strings
cannot work), we replace it with a genuine **deep copy** produced by round-tripping the value
through the serializer's own `StreamCodec` on the tick thread. The IO thread then only ever
encodes an immutable, freshly-decoded component that nothing else references or mutates — CME
becomes impossible for that value.

Why it closes the race: the offending mutation is on the tick thread, and now so is the copy,
so the two cannot interleave (same thread); the object handed to the packet is owned by nobody
else. See `SynchedDataSnapshots` for the full rationale.

### Verification (L3, RED→GREEN)
Reproduced on the Incus L3 client-join harness with a mod-free debug script that spawns a
tracked named entity and mutates its custom-name `siblings` list on the tick thread while
re-sending it:
- **RED** (v0.5.3 jar): the exact `set_entity_data` CME above fires and the client is kicked
  ("Internal Exception") within ~15s.
- **GREEN** (this fix): the guard fires (`first component entity-data snapshot taken`), no CME,
  the client survives, selftest passes.

Design properties:
- **No compile-time dependency on any third-party mod** — the target is vanilla
  `SynchedEntityData` + the two public vanilla `Component` serializers.
- **Pass-through by default** — every other entity-data value (ints, floats, BlockPos, item
  stacks, …) is returned by reference after one cheap reference check, so normal entity sync
  is untouched.
- **Degrades gracefully** — if the current server/registry is unavailable or the round-trip
  throws, the original value is returned unchanged (status quo) and the failure is logged
  once, never thrown onto the tick thread.
- **Both physical sides** — not restricted to the dedicated server, so single-player
  (integrated server inside the client jar) is guarded too.

Future pack fixes of the same shape can be added by extending `SynchedDataSnapshots`' target
set.

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
