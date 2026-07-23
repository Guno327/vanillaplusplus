package dev.vanillaplusplus.vppquests.quest;

import dev.vanillaplusplus.vppquests.VppQuests;
import dev.vanillaplusplus.vppquests.data.ModAttachments;
import dev.vanillaplusplus.vppquests.network.QuestDefinitionsSyncPayload;
import dev.vanillaplusplus.vppquests.network.QuestProgressSyncPayload;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.AddReloadListenerEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.neoforged.neoforge.server.ServerLifecycleHooks;

/**
 * Server-side lifecycle wiring: registers {@link QuestReloadListener} with
 * the datapack reload pipeline, syncs quest definitions + progress to a
 * player on login, and drives {@link QuestProgressTracker} on a throttled
 * server tick. Kept as one small event-handler class (matches
 * {@code vppintegration}'s precedent of one focused bridge class per
 * concern) rather than folding this into {@link VppQuests}'s constructor.
 */
@EventBusSubscriber(modid = VppQuests.MODID)
public final class ServerQuestEvents {

    private static final int EVALUATE_EVERY_N_TICKS = 20; // once per second - matches quests.js's own tick-scan cadence

    private static int tickCounter = 0;

    @SubscribeEvent
    static void onAddReloadListener(AddReloadListenerEvent event) {
        event.addListener(new QuestReloadListener());
    }

    @SubscribeEvent
    static void onPlayerLoggedIn(PlayerEvent.PlayerLoggedInEvent event) {
        if (event.getEntity() instanceof ServerPlayer serverPlayer) {
            syncAllToPlayer(serverPlayer);
        }
    }

    @SubscribeEvent
    static void onServerTick(ServerTickEvent.Post event) {
        tickCounter++;
        if (tickCounter < EVALUATE_EVERY_N_TICKS) {
            return;
        }
        tickCounter = 0;

        var server = ServerLifecycleHooks.getCurrentServer();
        if (server == null) {
            return;
        }
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            QuestProgressTracker.evaluate(player);
        }
    }

    private static void syncAllToPlayer(ServerPlayer player) {
        PacketDistributor.sendToPlayer(player, new QuestDefinitionsSyncPayload(QuestSyncFormat.serialize(QuestRegistry.get())));
        PacketDistributor.sendToPlayer(player, new QuestProgressSyncPayload(player.getData(ModAttachments.QUEST_PROGRESS).toJson()));
    }

    private ServerQuestEvents() {
    }
}
