package dev.vanillaplusplus.vppfixes;

import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Vanilla++ Fixes: a small home for hand-rolled, pack-specific correctness fixes to
 * third-party mods that can only be expressed as bytecode (Mixin) rather than config
 * or datapack overrides. Custom mods are an owner-approved exception to the pack's
 * No-New-Mods rule, tracked separately under {@code mods-src/} (this is the pack's
 * third, after vppintegration and vppquests).
 *
 * <p><b>First and only fix so far (GitHub #143):</b> a tracked entity's <b>custom name</b>
 * crashes the entity-data network path with a {@link java.util.ConcurrentModificationException}.
 * The custom name is a {@link net.minecraft.network.chat.Component} synced via the vanilla
 * {@code OPTIONAL_COMPONENT} {@link net.minecraft.network.syncher.EntityDataSerializer}
 * ({@code EntityDataSerializer.forValueType(ComponentSerialization.TRUSTED_OPTIONAL_STREAM_CODEC)}),
 * whose {@code copy(T)} is the identity function. When a mod stores a live, mutated
 * {@code MutableComponent} as the name and keeps appending to its {@code siblings}
 * {@link java.util.ArrayList} on the server tick thread, the entity-tracker packs that SAME
 * object and serializes it on the Netty IO thread ({@code SynchedEntityData$DataValue.write}
 * -&gt; {@code ComponentSerialization.CODEC}: {@code Codec.recursive} -&gt; {@code EitherCodec}
 * -&gt; {@code RecordCodecBuilder} -&gt; {@code OptionalFieldCodec} -&gt; {@code ListCodec}
 * over the siblings list). The tick-thread mutation races the IO-thread {@code ListCodec.encode}
 * iteration and throws CME, failing to encode {@code clientbound/minecraft:set_entity_data}
 * and disconnecting the tracking client ("Internal Exception"). Dedicated-server only: the
 * integrated server encodes on the server thread, so there is no race.
 *
 * <p><b>Correction to the original v0.5.3 diagnosis.</b> v0.5.3 guessed Ars Nouveau's
 * {@code ars_nouveau:spell_resolver} and matched serializers by registry-id string. That was
 * a double no-op: (1) {@code spell_resolver} uses a hand-written {@code StreamCodec} that
 * cannot produce the DFU {@code ListCodec} frames in the crash, and (2) vanilla serializers
 * are not registered in {@code NeoForgeRegistries.ENTITY_DATA_SERIALIZERS} (only modded ones
 * are), so they have no registry id and the id-string match could never fire. Reproduced
 * RED-&gt;GREEN on the L3 client-join test to confirm (see README / issue #143).
 *
 * <p><b>The fix</b> lives entirely in {@link dev.vanillaplusplus.vppfixes.mixin.SynchedEntityDataMixin}
 * + {@link SynchedDataSnapshots}: it takes a genuine deep copy of the offending component at
 * pack time (which runs on the server tick/main thread, see that class' doc) so the IO thread
 * only ever encodes an immutable snapshot that nothing mutates. It discriminates the two
 * vanilla component serializers by reference identity, so it carries NO compile-time
 * dependency on any third-party mod and is a cheap pass-through for every other value.
 */
@Mod(VppFixes.MODID)
public final class VppFixes {
    public static final String MODID = "vppfixes";
    public static final Logger LOGGER = LoggerFactory.getLogger("VanillaPlusPlus-Fixes");

    public VppFixes(IEventBus modEventBus, ModContainer modContainer) {
        LOGGER.info("vppfixes loaded: COMPONENT/OPTIONAL_COMPONENT entity-data CME guard active (GitHub #143)");
    }
}
