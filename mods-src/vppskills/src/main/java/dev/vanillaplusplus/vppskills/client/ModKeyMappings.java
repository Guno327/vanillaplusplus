package dev.vanillaplusplus.vppskills.client;

import com.mojang.blaze3d.platform.InputConstants;
import dev.vanillaplusplus.vppskills.VppSkills;
import net.minecraft.client.KeyMapping;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.settings.KeyConflictContext;
import net.neoforged.neoforge.client.event.RegisterKeyMappingsEvent;
import org.lwjgl.glfw.GLFW;

/**
 * Debug keybind for the phase-1 skill tree preview screen, per issue #163's
 * scope ("Bind the screen to a keybind or a debug command so it can be
 * opened; it does NOT need to be the live skill GUI yet"). {@code P} is
 * unused by both vanilla defaults and this pack's other custom mods
 * ({@code K} is vppquests' own quest-book key - see its
 * {@code ModKeyMappings}) - picked as a mnemonic-free placeholder since
 * this key binding itself is a phase-1 throwaway, not a shipped affordance.
 */
@EventBusSubscriber(modid = VppSkills.MODID, value = Dist.CLIENT)
public final class ModKeyMappings {

    private static final String CATEGORY = "key.categories.vppskills";

    public static final KeyMapping OPEN_SKILL_TREE_SCREEN = new KeyMapping(
            "key.vppskills.open_skill_tree",
            KeyConflictContext.IN_GAME,
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_P,
            CATEGORY);

    @SubscribeEvent
    static void register(RegisterKeyMappingsEvent event) {
        event.register(OPEN_SKILL_TREE_SCREEN);
    }

    private ModKeyMappings() {
    }
}
