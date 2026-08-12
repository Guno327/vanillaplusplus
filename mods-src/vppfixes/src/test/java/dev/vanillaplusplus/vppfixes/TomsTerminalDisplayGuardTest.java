package dev.vanillaplusplus.vppfixes;

import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Pins the real compare-and-set log-once semantics of {@link TomsTerminalDisplayGuard}:
 * each gate flips from {@code false} to {@code true} on its first call and stays
 * {@code true} (no further log) on every later call, and the three gates never
 * touch one another.
 *
 * <p>The three {@link AtomicBoolean} gates are {@code private static} fields with
 * no reset seam (no package-private accessor, no instance state, by design -
 * they exist to fire at most once per JVM lifetime, matching a real server
 * process). Rather than add a gratuitous reset/visibility seam to production
 * code purely to make this easier to test, this whole scenario runs inside a
 * SINGLE test method: each gate is touched exactly once across the entire test
 * class, since JUnit gives no ordering guarantee that would let a second test
 * method safely observe "still false" for a gate a prior method may already
 * have flipped. The gate values themselves are read via reflection (test-only,
 * no production visibility change) since the public methods are {@code void}
 * and only observable through this internal state or actual log output.
 */
class TomsTerminalDisplayGuardTest {

    @Test
    void logOnceGatesFireOnlyOnceAndAreIndependent() throws ReflectiveOperationException {
        AtomicBoolean offThread = gate("LOGGED_OFFTHREAD_DISABLED");
        AtomicBoolean multithread = gate("LOGGED_MULTITHREAD_FAILURE");
        AtomicBoolean stream = gate("LOGGED_STREAM_FAILURE");

        assertFalse(offThread.get(), "offThread gate must start unflipped");
        assertFalse(multithread.get(), "multithread gate must start unflipped");
        assertFalse(stream.get(), "stream gate must start unflipped");

        TomsTerminalDisplayGuard.logOffThreadDisabledOnce();

        assertTrue(offThread.get(), "first call must flip its own gate");
        assertFalse(multithread.get(), "an unrelated gate must stay untouched");
        assertFalse(stream.get(), "an unrelated gate must stay untouched");

        TomsTerminalDisplayGuard.logOffThreadDisabledOnce();
        assertTrue(offThread.get(), "gate stays flipped (idempotent) after a second call");

        TomsTerminalDisplayGuard.logMultithreadProcessingFailureOnce(new RuntimeException("boom"));
        assertTrue(multithread.get(), "second gate flips on its own first call");
        assertFalse(stream.get(), "third gate still untouched by the other two");

        TomsTerminalDisplayGuard.logStreamWrappedStacksFailureOnce(new RuntimeException("boom"));
        assertTrue(stream.get(), "third gate flips on its own first call");
    }

    private static AtomicBoolean gate(String fieldName) throws ReflectiveOperationException {
        Field field = TomsTerminalDisplayGuard.class.getDeclaredField(fieldName);
        field.setAccessible(true);
        return (AtomicBoolean) field.get(null);
    }
}
