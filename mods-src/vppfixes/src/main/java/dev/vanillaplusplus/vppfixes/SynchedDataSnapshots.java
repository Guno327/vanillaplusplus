package dev.vanillaplusplus.vppfixes;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import net.minecraft.core.RegistryAccess;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.syncher.EntityDataSerializer;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.MinecraftServer;
import net.neoforged.neoforge.server.ServerLifecycleHooks;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Deep-copies the two mutable, list-backed vanilla {@link SynchedEntityData.DataValue}s
 * (a text {@link net.minecraft.network.chat.Component}: {@code COMPONENT} and
 * {@code OPTIONAL_COMPONENT}, i.e. an entity's custom name) at pack time so the Netty IO
 * thread never serializes a component whose {@code siblings}/{@code extra} {@code ArrayList}
 * is being mutated on the server tick thread. GitHub #143.
 *
 * <p><b>Correction to the v0.5.3 diagnosis.</b> v0.5.3 targeted
 * {@code ars_nouveau:spell_resolver}. That was wrong: the real production stack encodes a
 * <i>Component</i> serializer ({@code ComponentSerialization.CODEC}: {@code Codec.recursive}
 * -&gt; {@code EitherCodec} -&gt; {@code RecordCodecBuilder} -&gt; {@code OptionalFieldCodec}
 * -&gt; {@code ListCodec} over the siblings {@code ArrayList}), not the hand-written
 * {@code SpellResolver.STREAM}. Ars 5.12.1's serialized graph is immutable/concurrent-safe
 * and never produces those DFU frames. See README / issue #143.
 *
 * <p><b>Why match by reference, not registry-id string.</b> NeoForge keeps <i>vanilla</i>
 * {@code EntityDataSerializers} in the int-id bimap (ids 0-255) and only registers
 * <i>modded</i> serializers into {@code NeoForgeRegistries.ENTITY_DATA_SERIALIZERS}
 * (see {@code CommonHooks#getSerializerId}). So the vanilla component serializers have
 * <b>no {@code ResourceLocation} key</b> ({@code getKey(..)} returns {@code null}) and the
 * old id-string approach could never match them. We therefore discriminate by serializer
 * <b>reference identity</b> against the two public vanilla constants.
 */
public final class SynchedDataSnapshots {

    private SynchedDataSnapshots() {
    }

    private static final AtomicBoolean LOGGED_FAILURE = new AtomicBoolean(false);
    private static final AtomicBoolean LOGGED_FIRST_SNAPSHOT = new AtomicBoolean(false);

    public static List<SynchedEntityData.DataValue<?>> snapshotTargeted(List<SynchedEntityData.DataValue<?>> values) {
        if (values == null || values.isEmpty()) {
            return values;
        }
        List<SynchedEntityData.DataValue<?>> copy = null;
        for (int i = 0; i < values.size(); i++) {
            SynchedEntityData.DataValue<?> dv = values.get(i);
            if (dv == null || !isTargeted(dv.serializer())) {
                continue;
            }
            SynchedEntityData.DataValue<?> snapshot = deepCopy(dv);
            if (snapshot == dv) {
                continue; // copy failed/degraded -> leave as-is
            }
            if (copy == null) {
                copy = new ArrayList<>(values);
            }
            copy.set(i, snapshot);
        }
        return copy == null ? values : copy;
    }

    /**
     * Reference match against the two vanilla component serializers. These are the
     * Codec-backed ({@code ComponentSerialization}) serializers whose value holds a
     * mutable {@code siblings ArrayList}; every other entity-data value (ints, floats,
     * BlockPos, item stacks, and the Ars stream-codec values) is passed through.
     */
    private static boolean isTargeted(EntityDataSerializer<?> serializer) {
        return serializer == EntityDataSerializers.COMPONENT
                || serializer == EntityDataSerializers.OPTIONAL_COMPONENT;
    }

    private static <T> SynchedEntityData.DataValue<T> deepCopy(SynchedEntityData.DataValue<T> dv) {
        MinecraftServer server = ServerLifecycleHooks.getCurrentServer();
        if (server == null) {
            return dv;
        }
        RegistryAccess registryAccess = server.registryAccess();
        StreamCodec<? super RegistryFriendlyByteBuf, T> codec = dv.serializer().codec();
        ByteBuf backing = Unpooled.buffer();
        try {
            RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(backing, registryAccess);
            codec.encode(buf, dv.value());
            T copied = codec.decode(buf);
            if (LOGGED_FIRST_SNAPSHOT.compareAndSet(false, true)) {
                VppFixes.LOGGER.info("vppfixes: first component entity-data snapshot taken (id {}) - CME guard is firing", dv.id());
            }
            return new SynchedEntityData.DataValue<>(dv.id(), dv.serializer(), copied);
        } catch (Throwable t) {
            if (LOGGED_FAILURE.compareAndSet(false, true)) {
                VppFixes.LOGGER.warn(
                        "vppfixes: failed to snapshot entity-data component value (id {}); leaving it unguarded. "
                                + "Logged once.", dv.id(), t);
            }
            return dv;
        } finally {
            backing.release();
        }
    }
}
