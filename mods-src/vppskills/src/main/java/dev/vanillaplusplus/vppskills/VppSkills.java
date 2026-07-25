package dev.vanillaplusplus.vppskills;

import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Vanilla++'s own Path-of-Exile-style skill-tree GUI (GitHub issue #163) -
 * meant to eventually replace puffish_skills' built-in tree screen. This is
 * the PHASE 1 FOUNDATION only: the tree data model ported from puffish_skills'
 * generated JSON (see {@code tree/SkillTreeLoader}) and a pannable/zoomable
 * proof-of-concept canvas ({@code client.gui.SkillTreeScreen}), opened by a
 * debug keybind. It deliberately has NO point/XP economy, no attribute-reward
 * application, no save-data persistence, no client-sync network payloads, no
 * respec, and is NOT wired into {@code pack/manifest.json} - puffish_skills
 * remains the pack's real, shipped skill system. See this mod's README.md
 * for the full phase-2+ plan.
 */
@Mod(VppSkills.MODID)
public final class VppSkills {
    public static final String MODID = "vppskills";
    public static final Logger LOGGER = LoggerFactory.getLogger(MODID);

    public VppSkills(IEventBus modEventBus, ModContainer modContainer) {
        LOGGER.info("vppskills loaded (phase 1 foundation - not wired into the pack's mod set)");
    }
}
