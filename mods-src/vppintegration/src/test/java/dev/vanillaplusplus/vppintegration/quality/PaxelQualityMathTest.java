package dev.vanillaplusplus.vppintegration.quality;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class PaxelQualityMathTest {

    // --- combine(forgeRollLevel, inputQualityLevel) ---

    @Test
    void combine_masterRollWithMasterInput_staysMaster() {
        assertEquals(5, PaxelQualityMath.combine(5, 5));
    }

    @Test
    void combine_masterRollWithPoorInput_dropsToPoor() {
        assertEquals(1, PaxelQualityMath.combine(5, 1));
    }

    @Test
    void combine_poorRollWithMasterInput_isCappedByTheRoll() {
        // Input quality can only scale the roll DOWN, never up - a poor roll
        // stays poor even with perfect input heads.
        assertEquals(1, PaxelQualityMath.combine(1, 5));
    }

    @Test
    void combine_midRollWithMidInput_roundsDown() {
        // WELL(2) roll x WELL(2) input = 2 * (2/5) = 0.8 -> rounds to 1 (POOR).
        assertEquals(1, PaxelQualityMath.combine(2, 2));
    }

    @Test
    void combine_expertRollWithExpertInput_roundsToWell() {
        // EXPERT(3) roll x EXPERT(3) input = 3 * (3/5) = 1.8 -> rounds to 2 (WELL).
        assertEquals(2, PaxelQualityMath.combine(3, 3));
    }

    @Test
    void combine_resultNeverBelowMinLevel() {
        // 1 * (1/5) = 0.2 -> rounds to 0, clamped up to MIN_LEVEL (1, POOR).
        assertEquals(PaxelQualityMath.MIN_LEVEL, PaxelQualityMath.combine(1, 1));
    }

    @Test
    void combine_rejectsOutOfRangeLevels() {
        assertThrows(IllegalArgumentException.class, () -> PaxelQualityMath.combine(0, 3));
        assertThrows(IllegalArgumentException.class, () -> PaxelQualityMath.combine(6, 3));
        assertThrows(IllegalArgumentException.class, () -> PaxelQualityMath.combine(3, 0));
        assertThrows(IllegalArgumentException.class, () -> PaxelQualityMath.combine(3, 6));
    }

    // --- averageLevel(levels...) ---

    @Test
    void averageLevel_roundsToNearestInteger() {
        assertEquals(2, PaxelQualityMath.averageLevel(1, 2, 3)); // mean 2.0
        assertEquals(1, PaxelQualityMath.averageLevel(1, 1, 2)); // mean 1.33 -> 1
        assertEquals(5, PaxelQualityMath.averageLevel(5, 5, 5)); // mean 5.0
    }

    @Test
    void averageLevel_roundsUpAtHalfway() {
        // mean 1.5 -> Math.round rounds half-up to 2.
        assertEquals(2, PaxelQualityMath.averageLevel(1, 2));
    }

    @Test
    void averageLevel_worksWithSingleValue() {
        assertEquals(4, PaxelQualityMath.averageLevel(4));
    }

    @Test
    void averageLevel_rejectsEmptyOrOutOfRangeLevels() {
        assertThrows(IllegalArgumentException.class, PaxelQualityMath::averageLevel);
        assertThrows(IllegalArgumentException.class, () -> PaxelQualityMath.averageLevel(1, 2, 0));
        assertThrows(IllegalArgumentException.class, () -> PaxelQualityMath.averageLevel(1, 2, 6));
    }
}
