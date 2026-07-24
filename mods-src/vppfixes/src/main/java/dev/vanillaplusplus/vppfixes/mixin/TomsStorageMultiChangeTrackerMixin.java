package dev.vanillaplusplus.vppfixes.mixin;

import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.tom.storagemod.inventory.StoredItemStack;
import dev.vanillaplusplus.vppfixes.TomsTerminalDisplayGuard;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

import java.util.List;
import java.util.stream.Stream;

/**
 * GitHub #165 -- Tom's Simple Storage 2.3.2's terminal shows no items to pull out (insert
 * still works). Ground-truthed via {@code javap}/decompile against
 * {@code server/mods/toms_storage-1.21-2.3.2.jar}:
 *
 * <p>{@code StorageTerminalBlockEntity.updateServer()} (called every server tick for a
 * placed terminal, see {@code com.tom.storagemod.util.TickerUtil$TickableServer}) rebuilds
 * its displayed item map from {@code tracker.getChangeTracker(level)} +
 * {@code tracker.streamWrappedStacks(...)}, with no try/catch around either call. When the
 * terminal's backing handler is a
 * {@code com.tom.storagemod.inventory.MultiInventoryAccess} (true for any terminal
 * connected to more than a single trivial inventory) and Tom's own
 * {@code runMultithreaded} config is {@code true} (its shipped default), both calls can run
 * work on {@link java.util.concurrent.ForkJoinPool#commonPool()} worker threads instead of
 * the calling (server main) thread:
 *
 * <ul>
 *   <li>{@code MultiChangeTracker.multithreadProcessing(Level)} dispatches each connected
 *       inventory's {@code TrackerInfo::run} (-&gt; {@code IMultiThreadedTracker.processOffThread})
 *       via {@code infos.parallelStream().unordered().peek(...).toArray()}.</li>
 *   <li>{@code MultiChangeTracker.streamWrappedStacks(true)} similarly fans the per-inventory
 *       item lists out via {@code .toList().parallelStream().flatMap(Collection::parallelStream)}.</li>
 * </ul>
 *
 * <p>Sophisticated Storage's {@code IItemHandler} is not safe to read concurrently with the
 * main thread mutating it (GitHub #70 pulled Sophisticated Storage in; this is a regression
 * from that). An exception thrown on one of those worker threads propagates back out of the
 * {@code parallelStream()...toArray()}/{@code flatMap} call on the calling thread, aborting
 * the whole list rebuild uncaught -- {@code StorageTerminalBlockEntity.items} is never
 * reassigned, so the terminal keeps showing an empty (or stale) list forever. Insert uses a
 * separate synchronous path ({@code pushStack} -&gt; {@code IInventoryAccess.pushStack}), so it
 * is unaffected and keeps working, matching the reported symptom exactly.
 *
 * <p>Fix, independent of the {@code runMultithreaded} config value (a config-seed default of
 * {@code false} also ships in {@code pack/defaultconfigs/toms_storage-server.toml} as a
 * belt-and-suspenders measure, but only seeds new worlds):
 *
 * <ul>
 *   <li>{@link #vppfixes$forceSequentialTrackerInfoStream} redirects the
 *       {@code infos.parallelStream()} call inside {@code multithreadProcessing} to a plain
 *       sequential {@code .stream()}, so {@code processOffThread} always runs on whichever
 *       thread called {@code getChangeTracker} (the server main thread, since block entity
 *       ticking is main-thread-only) -- never a ForkJoinPool worker.</li>
 *   <li>{@link #vppfixes$guardMultithreadProcessing} wraps the whole method in a try/catch
 *       as defense in depth: any surviving exception is logged once and treated as "no
 *       change this tick" instead of aborting the caller.</li>
 *   <li>{@link #vppfixes$guardStreamWrappedStacks} always calls the original method with
 *       {@code parallel=false} (bypassing its {@code parallelStream()}/{@code Collection::parallelStream}
 *       branch entirely, regardless of what the caller asked for) and wraps it in the same
 *       try/catch, degrading to an empty stream on failure.</li>
 * </ul>
 *
 * <p>Note: this mod's {@code Mixin} annotation has no {@code required} attribute (not
 * supported by this Mixin version); {@code toms_storage} is declared as an OPTIONAL AFTER
 * dependency in {@code neoforge.mods.toml} purely for load ordering. This pack always ships
 * {@code toms_storage}, so the config-level {@code "required": true} in
 * {@code vppfixes.mixins.json} applying to this mixin is not expected to bite in practice.
 */
@Mixin(targets = "com.tom.storagemod.inventory.MultiInventoryAccess$MultiChangeTracker", remap = false)
public abstract class TomsStorageMultiChangeTrackerMixin {

    @WrapOperation(
            method = "multithreadProcessing",
            at = @At(value = "INVOKE", target = "Ljava/util/List;parallelStream()Ljava/util/stream/Stream;")
    )
    private <T> Stream<T> vppfixes$forceSequentialTrackerInfoStream(List<T> infos, Operation<Stream<T>> original) {
        TomsTerminalDisplayGuard.logOffThreadDisabledOnce();
        return infos.stream();
    }

    @WrapMethod(method = "multithreadProcessing")
    private boolean vppfixes$guardMultithreadProcessing(Level level, Operation<Boolean> original) {
        try {
            return original.call(level);
        } catch (Throwable t) {
            TomsTerminalDisplayGuard.logMultithreadProcessingFailureOnce(t);
            return false;
        }
    }

    @WrapMethod(method = "streamWrappedStacks")
    private Stream<StoredItemStack> vppfixes$guardStreamWrappedStacks(boolean parallel, Operation<Stream<StoredItemStack>> original) {
        try {
            // Always take the sequential branch (parallel=false) regardless of what the
            // caller requested - see class doc: this is the second off-thread hazard,
            // independent of multithreadProcessing above.
            return original.call(false);
        } catch (Throwable t) {
            TomsTerminalDisplayGuard.logStreamWrappedStacksFailureOnce(t);
            return Stream.empty();
        }
    }
}
