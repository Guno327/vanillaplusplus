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
 *
 * <p><b>No legacy-progress migration.</b> An earlier revision of this mod
 * had a {@code QuestLegacyMigration} step here that carried a player's
 * already-complete quests forward out of the old KubeJS quest tracker's
 * save file. GitHub #109's cutover removed it: the owner reported the old
 * system was broken end to end (progress wasn't being recognized at all),
 * so there was nothing correct left to migrate, and the owner explicitly
 * asked not to carry old quest/progress data forward - {@code vppquests}
 * is the sole quest system now, starting fresh for every player.
 */
@EventBusSubscriber(modid = VppQuests.MODID)
public final class ServerQuestEvents {

    private static final int EVALUATE_EVERY_N_TICKS = 20; // once per second - a steady, cheap tick-scan cadence

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
