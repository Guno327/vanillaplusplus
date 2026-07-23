package dev.vanillaplusplus.vppquests.client;

import com.mojang.blaze3d.platform.InputConstants;
import dev.vanillaplusplus.vppquests.VppQuests;
import net.minecraft.client.KeyMapping;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.settings.KeyConflictContext;
import net.neoforged.neoforge.client.event.RegisterKeyMappingsEvent;
import org.lwjgl.glfw.GLFW;

/**
 * The quest screen's keybind - same affordance as vanilla's own {@code L}
 * key for the advancements screen, per DESIGN.md's #109 design-proposal
 * section ("opened via a keybind... same affordance as vanilla's L key").
 * {@code K} is used instead of {@code L} since {@code L} is vanilla's own
 * hard-bound advancements key, still active in this scaffold's Phase A
 * (the old advancement-based quest GUI layer isn't touched/removed yet).
 */
@EventBusSubscriber(modid = VppQuests.MODID, value = Dist.CLIENT)
public final class ModKeyMappings {

    private static final String CATEGORY = "key.categories.vppquests";

    public static final KeyMapping OPEN_QUEST_SCREEN = new KeyMapping(
            "key.vppquests.open_quests",
            KeyConflictContext.IN_GAME,
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_K,
            CATEGORY);

    @SubscribeEvent
    static void register(RegisterKeyMappingsEvent event) {
        event.register(OPEN_QUEST_SCREEN);
    }

    private ModKeyMappings() {
    }
}
