package dev.vanillaplusplus.vppfixes;

import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Log-once helpers for {@link dev.vanillaplusplus.vppfixes.mixin.TomsStorageMultiChangeTrackerMixin}
 * (GitHub #165). Kept out of the mixin class itself so the mixin stays a thin set of
 * injector methods, matching the existing {@link SynchedDataSnapshots} split.
 */
public final class TomsTerminalDisplayGuard {

    private TomsTerminalDisplayGuard() {
    }

    private static final AtomicBoolean LOGGED_OFFTHREAD_DISABLED = new AtomicBoolean(false);
    private static final AtomicBoolean LOGGED_MULTITHREAD_FAILURE = new AtomicBoolean(false);
    private static final AtomicBoolean LOGGED_STREAM_FAILURE = new AtomicBoolean(false);

    public static void logOffThreadDisabledOnce() {
        if (LOGGED_OFFTHREAD_DISABLED.compareAndSet(false, true)) {
            VppFixes.LOGGER.info(
                    "vppfixes: Tom's Simple Storage terminal display-list build forced onto the calling "
                            + "(main) thread - GitHub #165 (off-thread reads of Sophisticated Storage's "
                            + "non-thread-safe IItemHandler were aborting the list build).");
        }
    }

    public static void logMultithreadProcessingFailureOnce(Throwable t) {
        if (LOGGED_MULTITHREAD_FAILURE.compareAndSet(false, true)) {
            VppFixes.LOGGER.warn(
                    "vppfixes: Tom's Simple Storage terminal change-tracker refresh threw; degrading "
                            + "gracefully (treating this tick as \"no change\") instead of aborting the whole "
                            + "list build. Logged once. GitHub #165.", t);
        }
    }

    public static void logStreamWrappedStacksFailureOnce(Throwable t) {
        if (LOGGED_STREAM_FAILURE.compareAndSet(false, true)) {
            VppFixes.LOGGER.warn(
                    "vppfixes: Tom's Simple Storage terminal item-list stream threw; degrading gracefully "
                            + "(returning an empty stream for this refresh) instead of aborting the whole "
                            + "list build. Logged once. GitHub #165.", t);
        }
    }
}
