package dev.vanillaplusplus.vppskills.client;

import dev.vanillaplusplus.vppskills.VppSkills;
import dev.vanillaplusplus.vppskills.client.gui.SkillTreeScreen;
import net.minecraft.client.Minecraft;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;

/**
 * Opens {@link SkillTreeScreen} when {@link ModKeyMappings#OPEN_SKILL_TREE_SCREEN}
 * is pressed in-game - same tick-poll pattern as vppquests'
 * {@code ClientQuestEvents} (see that class), proven working there.
 */
@EventBusSubscriber(modid = VppSkills.MODID, value = Dist.CLIENT)
public final class ClientSkillTreeEvents {

    @SubscribeEvent
    static void onClientTick(ClientTickEvent.Post event) {
        Minecraft minecraft = Minecraft.getInstance();
        while (ModKeyMappings.OPEN_SKILL_TREE_SCREEN.consumeClick()) {
            if (minecraft.screen == null) {
                minecraft.setScreen(new SkillTreeScreen());
            }
        }
    }

    private ClientSkillTreeEvents() {
    }
}
