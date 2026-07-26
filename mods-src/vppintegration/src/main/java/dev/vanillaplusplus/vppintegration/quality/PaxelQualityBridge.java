package dev.vanillaplusplus.vppintegration.quality;

import net.stirdrem.overgeared.ForgingQuality;

import java.util.List;

/**
 * Thin {@code ForgingQuality} &lt;-&gt; integer-level adapter over {@link
 * PaxelQualityMath}'s pure arithmetic, used by {@code
 * dev.vanillaplusplus.vppintegration.mixin.PaxelHeadForgingMixin} to compute the
 * GitHub #67 Phase 3 paxel head's combined quality (forge roll x input parts'
 * quality) without duplicating the level math there.
 *
 * <p>Kept separate from {@link PaxelQualityMath} specifically so that class has
 * no Overgeared/Minecraft imports and stays unit-testable on a bare JVM
 * classpath; this class exists purely to translate at the boundary.
 */
public final class PaxelQualityBridge {
    private PaxelQualityBridge() {}

    /**
     * Combines {@code forgeRoll} (the quality actually rolled assembling the
     * paxel head at the anvil) with the derived quality of the input heads
     * (the average of their own already-rolled {@code ForgingQuality}), per
     * {@link PaxelQualityMath#combine(int, int)}.
     *
     * <p>{@code ForgingQuality.NONE} (on either the roll or an input head) is
     * treated as {@code WELL} - the same "no quality yet" fallback {@code
     * OvergearedSilentGearBridge} already uses for unforged Silent Gear items -
     * rather than crashing on a level outside {@code [POOR, MASTER]}.
     */
    public static ForgingQuality combineQuality(ForgingQuality forgeRoll, List<ForgingQuality> inputQualities) {
        if (inputQualities == null || inputQualities.isEmpty()) {
            throw new IllegalArgumentException("inputQualities must not be empty");
        }

        int forgeRollLevel = levelOf(forgeRoll);
        int[] inputLevels = new int[inputQualities.size()];
        for (int i = 0; i < inputQualities.size(); i++) {
            inputLevels[i] = levelOf(inputQualities.get(i));
        }

        int inputQualityLevel = PaxelQualityMath.averageLevel(inputLevels);
        int combinedLevel = PaxelQualityMath.combine(forgeRollLevel, inputQualityLevel);
        return qualityOf(combinedLevel);
    }

    /** {@code ForgingQuality} -> 1..5 level. {@code NONE} maps to the WELL(2) fallback. */
    private static int levelOf(ForgingQuality quality) {
        return switch (quality) {
            case POOR -> 1;
            case WELL -> 2;
            case EXPERT -> 3;
            case PERFECT -> 4;
            case MASTER -> 5;
            case NONE -> 2;
        };
    }

    /** 1..5 level -> {@code ForgingQuality}. Out-of-range falls back to WELL(2), same reasoning as {@link #levelOf}. */
    private static ForgingQuality qualityOf(int level) {
        return switch (level) {
            case 1 -> ForgingQuality.POOR;
            case 2 -> ForgingQuality.WELL;
            case 3 -> ForgingQuality.EXPERT;
            case 4 -> ForgingQuality.PERFECT;
            case 5 -> ForgingQuality.MASTER;
            default -> ForgingQuality.WELL;
        };
    }
}
