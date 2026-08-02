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
 * <p>Phase 2 added the direction-independent backend pieces needed before
 * any of that could become real: server-authoritative unlock validation
 * ({@code unlock.SkillUnlockValidator}), per-player persistence
 * ({@code data.SkillProgressAttachment}, registered below), an attribute
 * -operation translation layer from puffish_skills' reward vocabulary to
 * real NeoForge {@code AttributeModifier}s ({@code reward.AttributeOperationTranslator}),
 * and a progress-sync payload mirroring that state to the client
 * ({@code network.SkillProgressSyncPayload}).
 *
 * <p>Phase 3 (this revision) closes the interactive loop phase 2 deliberately
 * left open: a client-&gt;server unlock-request payload
 * ({@code network.SkillUnlockRequestPayload}), a server-side handler that
 * validates it against {@code unlock.SkillUnlockValidator} and re-syncs the
 * result ({@code server.ServerSkillEvents}, also wired to send-on-login), a
 * debug/placeholder {@code /vppskills grantpoints} command
 * ({@code command.VppSkillsCommand}) so the loop is exercisable without the
 * (still out-of-scope) real XP economy, and {@code client.gui.SkillTreeScreen}
 * now actually renders allocated/available/locked node states and sends real
 * unlock requests on click. This mod is still NOT wired into
 * {@code pack/manifest.json} - puffish_skills remains the pack's real,
 * shipped skill system throughout. See this mod's README.md for the full
 * phase plan and what remains for a later phase.
 */
@Mod(VppSkills.MODID)
public final class VppSkills {
    public static final String MODID = "vppskills";
    public static final Logger LOGGER = LoggerFactory.getLogger(MODID);

    public VppSkills(IEventBus modEventBus, ModContainer modContainer) {
        ModAttachments.ATTACHMENT_TYPES.register(modEventBus);
        LOGGER.info("vppskills loaded (phase 3 - interactive unlock loop wired, still not in the pack's mod set)");
    }
}
