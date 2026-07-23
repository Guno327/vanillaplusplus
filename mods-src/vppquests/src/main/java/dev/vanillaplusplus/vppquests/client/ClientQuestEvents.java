package dev.vanillaplusplus.vppquests.client;

import dev.vanillaplusplus.vppquests.VppQuests;
import dev.vanillaplusplus.vppquests.client.gui.QuestScreen;
import net.minecraft.client.Minecraft;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;

/** Opens {@link QuestScreen} when {@link ModKeyMappings#OPEN_QUEST_SCREEN} is pressed in-game. */
@EventBusSubscriber(modid = VppQuests.MODID, value = Dist.CLIENT)
public final class ClientQuestEvents {

    @SubscribeEvent
    static void onClientTick(ClientTickEvent.Post event) {
        Minecraft minecraft = Minecraft.getInstance();
        while (ModKeyMappings.OPEN_QUEST_SCREEN.consumeClick()) {
            if (minecraft.screen == null) {
                minecraft.setScreen(new QuestScreen());
            }
        }
    }

    private ClientQuestEvents() {
    }
}
