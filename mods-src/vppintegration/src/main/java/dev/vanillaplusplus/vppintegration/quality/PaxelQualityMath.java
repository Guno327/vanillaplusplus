package dev.vanillaplusplus.vppintegration.quality;

/**
 * Pure integer math for the GitHub #67 Phase 3 "Paxel" quality rule: the
 * assembled paxel head's Overgeared quality = the forge roll (the quality the
 * player actually rolled assembling the paxel head at the anvil) multiplied by
 * the input parts' quality (derived from the 3 combined heads' own already-rolled
 * quality, not a fresh default).
 *
 * <p>Deliberately has ZERO Minecraft/Overgeared imports (in particular, no
 * {@code net.stirdrem.overgeared.ForgingQuality}) so it can be unit tested on a
 * plain JVM classpath without NeoForge/Minecraft on the test runtime. {@code
 * ForgingQuality} <-> level conversion lives in {@link PaxelQualityBridge}, the
 * thin adapter that is this class's only caller in production code.
 *
 * <p><b>Level scale:</b> Overgeared's real {@code ForgingQuality} enum ordinals
 * (confirmed via {@code javap} against {@code server/mods/overgeared-*.jar}) are
 * {@code POOR(0), WELL(1), EXPERT(2), PERFECT(3), MASTER(4), NONE(5)} - this
 * class uses a 1-indexed "level" ({@code POOR=1 .. MASTER=5}) instead of the raw
 * ordinal so {@code NONE} (which does not represent a real quality grade) is
 * simply not a valid level, rather than sorting after {@code MASTER}.
 *
 * <p><b>The multiplication rule:</b> input quality acts as a fraction (0.2 for
 * POOR up to 1.0 for MASTER) that scales the forge roll level down - a MASTER
 * forge roll on POOR-quality input heads lands at POOR-ish output, while a MASTER
 * forge roll on MASTER-quality input heads stays MASTER. Multiplying the two
 * levels directly (both 1..5) without normalizing would let two good rolls
 * trivially blow past the 5-level scale (e.g. EXPERT(3) x EXPERT(3) = 9) and
 * would need clamping to mean anything close to "average" instead of "excellent"
 * - treating the input quality as a fraction keeps the result meaningfully
 * bounded by the forge roll itself, which is what "forge roll x input quality"
 * reads as: the forge roll is the base, input quality is the multiplier.
 */
public final class PaxelQualityMath {
    private PaxelQualityMath() {}

    /** Lowest real quality level (POOR). */
    public static final int MIN_LEVEL = 1;

    /** Highest real quality level (MASTER). */
    public static final int MAX_LEVEL = 5;

    /**
     * Combines a forge roll level with a derived input-quality level into the
     * final quality level, clamped to {@code [MIN_LEVEL, MAX_LEVEL]}.
     *
     * <p>{@code inputQualityLevel} is treated as a fraction of {@link
     * #MAX_LEVEL} (e.g. level 3 of 5 = 60%) that scales {@code forgeRollLevel}
     * down; the result is rounded to the nearest integer level.
     *
     * @throws IllegalArgumentException if either argument is outside
     *     {@code [MIN_LEVEL, MAX_LEVEL]}
     */
    public static int combine(int forgeRollLevel, int inputQualityLevel) {
        validateLevel(forgeRollLevel, "forgeRollLevel");
        validateLevel(inputQualityLevel, "inputQualityLevel");

        double fraction = inputQualityLevel / (double) MAX_LEVEL;
        int combined = (int) Math.round(forgeRollLevel * fraction);
        return clamp(combined);
    }

    /**
     * Rounds the arithmetic mean of the given quality levels to the nearest
     * integer level, clamped to {@code [MIN_LEVEL, MAX_LEVEL]}. Used to derive
     * "the input parts' quality" from the 3 combined heads' individual rolled
     * qualities.
     *
     * @throws IllegalArgumentException if {@code levels} is empty or any entry
     *     is outside {@code [MIN_LEVEL, MAX_LEVEL]}
     */
    public static int averageLevel(int... levels) {
        if (levels == null || levels.length == 0) {
            throw new IllegalArgumentException("levels must not be empty");
        }
        int sum = 0;
        for (int level : levels) {
            validateLevel(level, "levels");
            sum += level;
        }
        int rounded = (int) Math.round(sum / (double) levels.length);
        return clamp(rounded);
    }

    private static int clamp(int level) {
        return Math.max(MIN_LEVEL, Math.min(MAX_LEVEL, level));
    }

    private static void validateLevel(int level, String name) {
        if (level < MIN_LEVEL || level > MAX_LEVEL) {
            throw new IllegalArgumentException(
                    name + " must be in [" + MIN_LEVEL + ", " + MAX_LEVEL + "], was " + level);
        }
    }
}
