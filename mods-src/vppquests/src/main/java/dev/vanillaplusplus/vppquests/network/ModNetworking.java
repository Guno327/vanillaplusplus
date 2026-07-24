package dev.vanillaplusplus.vppquests.network;

import dev.vanillaplusplus.vppquests.VppQuests;
import dev.vanillaplusplus.vppquests.client.ClientQuestState;
import dev.vanillaplusplus.vppquests.quest.QuestProgressTracker;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

/**
 * Registers this mod's sync/claim payloads (quest definitions, per-player
 * progress - see {@link QuestDefinitionsSyncPayload}/
 * {@link QuestProgressSyncPayload} for why each is a single JSON-string
 * payload rather than a fully typed stream codec in this Phase A scaffold -
 * plus the claim-on-hand-in request, {@link ClaimQuestRewardPayload}).
 *
 * <p>The client-side handler method reference ({@code ClientQuestState::apply*})
 * is safe to register from common code on a dedicated server: registering a
 * method reference only resolves the method's own class, it doesn't execute
 * the method body (which is the part that would touch client-only state) -
 * same pattern this codebase's own client-only payload handlers should
 * follow if more are added later.
 *
 * <p><b>Server-authoritative claim (GitHub #164 item 5).</b> The
 * {@link ClaimQuestRewardPayload} handler never trusts the client: it looks
 * up the real {@link ServerPlayer} the packet arrived from (never a
 * client-supplied identity) and delegates straight to
 * {@link QuestProgressTracker#claimReward}, which re-checks completion and
 * claimed state against that player's own server-side attachment before
 * granting anything. A forged or replayed packet for a not-yet-complete or
 * already-claimed quest is a silent no-op, not a duplicate grant.
 */
@EventBusSubscriber(modid = VppQuests.MODID)
public final class ModNetworking {

    @SubscribeEvent
    static void register(RegisterPayloadHandlersEvent event) {
        PayloadRegistrar registrar = event.registrar("1");

        registrar.playToClient(
                QuestDefinitionsSyncPayload.TYPE,
                QuestDefinitionsSyncPayload.STREAM_CODEC,
                (payload, context) -> context.enqueueWork(() -> ClientQuestState.applyDefinitions(payload.questsJson())));

        registrar.playToClient(
                QuestProgressSyncPayload.TYPE,
                QuestProgressSyncPayload.STREAM_CODEC,
                (payload, context) -> context.enqueueWork(() -> ClientQuestState.applyProgress(payload.progressJson())));

        registrar.playToServer(
                ClaimQuestRewardPayload.TYPE,
                ClaimQuestRewardPayload.STREAM_CODEC,
                (payload, context) -> context.enqueueWork(() -> {
                    if (context.player() instanceof ServerPlayer serverPlayer) {
                        QuestProgressTracker.claimReward(serverPlayer, payload.questId());
                    }
                }));
    }

    private ModNetworking() {
    }
}
