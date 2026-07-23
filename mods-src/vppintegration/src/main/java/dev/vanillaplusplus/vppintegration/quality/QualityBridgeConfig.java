package dev.vanillaplusplus.vppintegration.quality;

import net.neoforged.neoforge.common.ModConfigSpec;
import net.stirdrem.overgeared.ForgingQuality;

/**
 * Server config for the parts of this bridge that are pack-tuning knobs rather
 * than fixed integration behavior - kept separate from Overgeared's own
 * {@code ServerConfig} (which this mod reads from, not writes to) since these
 * values are specific to how Vanilla++ treats non-forged Silent Gear items, not
 * a general Overgeared setting.
 */
public final class QualityBridgeConfig {
    public static final ModConfigSpec SPEC;
    public static final ModConfigSpec.EnumValue<ForgingQuality> DEFAULT_UNFORGED_QUALITY;

    static {
        ModConfigSpec.Builder builder = new ModConfigSpec.Builder();
        builder.push("quality_bridge");
        DEFAULT_UNFORGED_QUALITY = builder
                .comment(
                        "Quality grade stamped onto a Silent Gear tool/weapon/armor piece the",
                        "first time it finishes assembling WITHOUT ever having been forged at",
                        "an Overgeared anvil (pattern-crafted parts, non-metal assemblies, any",
                        "other Silent Gear crafting path this pack keeps open). Never overwrites",
                        "a quality already present (i.e. never overwrites a real anvil roll).",
                        "Set to NONE to leave such items with no quality bonus at all instead."
                )
                .defineEnum("defaultUnforgedQuality", ForgingQuality.WELL);
        builder.pop();
        SPEC = builder.build();
    }

    private QualityBridgeConfig() {
    }
}
