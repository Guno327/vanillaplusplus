package dev.vanillaplusplus.vppfixes.mixin;

import com.llamalad7.mixinextras.injector.ModifyReturnValue;
import dev.vanillaplusplus.vppfixes.SynchedDataSnapshots;
import net.minecraft.network.syncher.SynchedEntityData;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

import java.util.List;

/**
 * Guards the server-to-client entity-data path against a {@link java.util.ConcurrentModificationException}
 * raised while encoding a mod-owned, list-backed {@code SynchedEntityData} value on the Netty
 * IO thread (GitHub #143 -- Ars Nouveau's {@code ars_nouveau:spell_resolver}).
 *
 * <p>Both hooked methods build the outgoing {@code List<DataValue<?>>} on the server tick
 * thread (called from {@code ServerEntity#sendChanges}/{@code #sendPairingData}); the packet
 * is only encoded later on the IO thread. Post-processing the return value here lets us take
 * a deep-copy snapshot of the offending value on the tick thread, so the IO thread only ever
 * serializes an object nothing else can mutate. See {@link SynchedDataSnapshots} for the full
 * rationale and the (narrow, id-keyed, pass-through-by-default) scope.
 *
 * <p>Deliberately NOT restricted to the physical server side: in single-player the integrated
 * server runs inside the client jar, so a client-excluded mixin would leave that case
 * unguarded. {@code ServerLifecycleHooks.getCurrentServer()} resolves the integrated server
 * there; on a remote client (where these methods are not used for sending) it returns null and
 * the snapshot degrades to a harmless pass-through.
 */
@Mixin(SynchedEntityData.class)
public abstract class SynchedEntityDataMixin {

    @ModifyReturnValue(method = "packDirty", at = @At("RETURN"))
    private List<SynchedEntityData.DataValue<?>> vppfixes$snapshotDirtyValues(List<SynchedEntityData.DataValue<?>> values) {
        return SynchedDataSnapshots.snapshotTargeted(values);
    }

    @ModifyReturnValue(method = "getNonDefaultValues", at = @At("RETURN"))
    private List<SynchedEntityData.DataValue<?>> vppfixes$snapshotNonDefaultValues(List<SynchedEntityData.DataValue<?>> values) {
        return SynchedDataSnapshots.snapshotTargeted(values);
    }
}
