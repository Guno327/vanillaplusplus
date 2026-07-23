package dev.vanillaplusplus.vppfixes;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import net.minecraft.core.RegistryAccess;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.syncher.EntityDataSerializer;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.neoforged.neoforge.registries.NeoForgeRegistries;
import net.neoforged.neoforge.server.ServerLifecycleHooks;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Deep-copies list/collection-backed {@link SynchedEntityData.DataValue}s at pack time so
 * the Netty IO thread never serializes a live, main-thread-mutated object graph.
 *
 * <p><b>Why this is safe / why it closes the race (GitHub #143).</b> The two entry points
 * ({@code SynchedEntityData#packDirty} and {@code #getNonDefaultValues}) are called from
 * {@code net.minecraft.server.level.ServerEntity#sendChanges}/{@code #sendPairingData},
 * which run on the server tick thread as part of chunk-map entity tracking. The
 * {@code ClientboundSetEntityDataPacket} they build is only <i>encoded</i> later, on the
 * Netty IO thread ({@code DataValue.write}). The offending mutation (Ars Nouveau spell
 * resolution mutating a nested list on the server tick thread) therefore races only the
 * IO-thread encode -- never the pack call. By producing a genuine deep copy <i>here</i>,
 * on the tick thread, the encode (via the serializer's own {@link StreamCodec}) is
 * serialized with any concurrent mutation on that same thread (no interleave possible),
 * and the fresh decoded object handed to the packet is owned by nobody else, so the
 * IO-thread encode iterates an immutable snapshot. CME becomes impossible for the targeted
 * value without changing any observable game behavior.
 *
 * <p><b>Scope.</b> Only serializers whose registry id is in {@link #TARGET_SERIALIZER_IDS}
 * are copied; every other value (the overwhelming majority: ints, floats, BlockPos, etc.)
 * is passed through by reference with a single cheap registry-key lookup, so normal entity
 * sync is untouched. The match is by string id, so this class needs no compile-time
 * dependency on Ars Nouveau and simply does nothing if that mod/serializer is absent.
 *
 * <p><b>Degradation.</b> If the current server or registry access is unavailable, or the
 * round-trip throws for any reason, the original {@code DataValue} is returned unchanged
 * (status quo -- no worse than before the fix) and the failure is logged once rather than
 * propagating an exception onto the tick thread.
 */
public final class SynchedDataSnapshots {

    private SynchedDataSnapshots() {
    }

    /**
     * Entity-data serializers known to hold a mutable, aliased object graph that the owning
     * mod keeps mutating on the server thread after {@code set(...)}. Keyed by registry id
     * string so no cross-mod compile dependency is needed. Add future offenders here.
     */
    private static final Set<String> TARGET_SERIALIZER_IDS = Set.of(
            // Ars Nouveau: EntityProjectileSpell / EntitySpellArrow sync a live SpellResolver
            // (Spell recipe list + Optional<TimelineMap> particle timeline) via forValueType,
            // whose copy() is identity. GitHub #143.
            "ars_nouveau:spell_resolver"
    );

    private static final AtomicBoolean LOGGED_FAILURE = new AtomicBoolean(false);

    /**
     * Returns {@code values} with any targeted entry replaced by a deep copy. Returns the
     * input list untouched (same instance) when nothing needed copying, to keep the common
     * path allocation-free.
     */
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

    private static boolean isTargeted(EntityDataSerializer<?> serializer) {
        if (serializer == null || TARGET_SERIALIZER_IDS.isEmpty()) {
            return false;
        }
        ResourceLocation id = NeoForgeRegistries.ENTITY_DATA_SERIALIZERS.getKey(serializer);
        return id != null && TARGET_SERIALIZER_IDS.contains(id.toString());
    }

    /**
     * Deep-copies a single {@code DataValue} by round-tripping its value through the
     * serializer's own {@link StreamCodec} on the current thread (the caller guarantees the
     * server tick thread; see the class doc). Returns the original {@code dv} unchanged if a
     * copy cannot be made.
     */
    private static <T> SynchedEntityData.DataValue<T> deepCopy(SynchedEntityData.DataValue<T> dv) {
        MinecraftServer server = ServerLifecycleHooks.getCurrentServer();
        if (server == null) {
            return dv; // no registry access available (e.g. remote client) -> pass through
        }
        RegistryAccess registryAccess = server.registryAccess();
        StreamCodec<? super RegistryFriendlyByteBuf, T> codec = dv.serializer().codec();
        ByteBuf backing = Unpooled.buffer();
        try {
            RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(backing, registryAccess);
            codec.encode(buf, dv.value());
            T copied = codec.decode(buf);
            return new SynchedEntityData.DataValue<>(dv.id(), dv.serializer(), copied);
        } catch (Throwable t) {
            if (LOGGED_FAILURE.compareAndSet(false, true)) {
                VppFixes.LOGGER.warn(
                        "vppfixes: failed to snapshot entity-data value (id {}); leaving it unguarded. "
                                + "This is logged once; the entity-data CME guard is a no-op for this value.",
                        dv.id(), t);
            }
            return dv;
        } finally {
            backing.release();
        }
    }
}
