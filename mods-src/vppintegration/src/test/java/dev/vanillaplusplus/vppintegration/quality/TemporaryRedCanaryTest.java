package dev.vanillaplusplus.vppintegration.quality;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * TEMPORARY - GitHub #183 acceptance criterion: "a deliberately failing Java
 * test is shown to turn the job red before the final green". This class exists
 * for exactly one CI run and is reverted in the next commit on this branch.
 */
class TemporaryRedCanaryTest {

    @Test
    void deliberatelyFails() {
        assertEquals(1, 2, "#183 red-before-green canary - this MUST fail");
    }
}
