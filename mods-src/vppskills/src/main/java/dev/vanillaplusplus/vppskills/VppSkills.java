package dev.vanillaplusplus.vppskills;

import dev.vanillaplusplus.vppskills.data.ModAttachments;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Vanilla++'s own Path-of-Exile-style skill-tree GUI (GitHub issue #163) -
 * meant to eventually replace puffish_skills' built-in tree screen.
 *
 * <p>Phase 1 (see this mod's README.md) ported the tree data model from
 * puffish_skills' generated JSON ({@code tree/SkillTreeLoader}) and a
 * pannable/zoomable proof-of-concept canvas ({@code client.gui.SkillTreeScreen}).
 *
 * <p>Phase 2 (this revision) adds the direction-independent backend pieces
 * needed before any of that can become real: server-authoritative unlock
 * validation ({@code unlock.SkillUnlockValidator}), per-player persistence
 * ({@code data.SkillProgressAttachment}, registered below), an attribute
 * -operation translation layer from puffish_skills' reward vocabulary to
 * real NeoForge {@code AttributeModifier}s ({@code reward.AttributeOperationTranslator}),
 * and a progress-sync payload mirroring that state to the client
 * ({@code network.SkillProgressSyncPayload}). None of this is wired to
 * {@code client.gui.SkillTreeScreen}'s clicks yet, no attribute rewards are
 * actually granted yet, and this mod is still NOT wired into
 * {@code pack/manifest.json} - puffish_skills remains the pack's real,
 * shipped skill system throughout. See this mod's README.md for the full
 * phase-2+ plan and what remains for a later phase.
 */
@Mod(VppSkills.MODID)
public final class VppSkills {
    public static final String MODID = "vppskills";
    public static final Logger LOGGER = LoggerFactory.getLogger(MODID);

    public VppSkills(IEventBus modEventBus, ModContainer modContainer) {
        ModAttachments.ATTACHMENT_TYPES.register(modEventBus);
        LOGGER.info("vppskills loaded (phase 2 backend - not wired into the pack's mod set)");
    }
}
