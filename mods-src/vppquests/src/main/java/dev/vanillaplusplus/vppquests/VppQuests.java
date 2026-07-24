package dev.vanillaplusplus.vppquests;

import dev.vanillaplusplus.vppquests.data.ModAttachments;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Vanilla++'s custom quest mod (GitHub issue #109) - Phase A scaffold: data
 * model, datapack-driven registry, a progress-tracking data attachment, and
 * definitions/progress client sync. See this mod's README.md and the parent
 * repo's DESIGN.md #109 design-proposal section for the full architecture
 * and phasing; Phases B-D (migration, cutover, questline rebuild) are
 * deliberately NOT part of this class or this mod yet.
 */
@Mod(VppQuests.MODID)
public final class VppQuests {
    public static final String MODID = "vppquests";
    public static final Logger LOGGER = LoggerFactory.getLogger(MODID);

    public VppQuests(IEventBus modEventBus, ModContainer modContainer) {
        ModAttachments.ATTACHMENT_TYPES.register(modEventBus);
        LOGGER.info("vppquests loaded (Phase A scaffold)");
    }
}
