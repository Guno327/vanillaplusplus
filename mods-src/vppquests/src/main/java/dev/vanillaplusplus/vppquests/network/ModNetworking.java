package dev.vanillaplusplus.vppquests.network;

import dev.vanillaplusplus.vppquests.VppQuests;
import dev.vanillaplusplus.vppquests.client.ClientQuestState;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

/**
 * Registers this mod's two sync payloads (quest definitions, per-player
 * progress - see {@link QuestDefinitionsSyncPayload}/
 * {@link QuestProgressSyncPayload} for why each is a single JSON-string
 * payload rather than a fully typed stream codec in this Phase A scaffold).
 *
 * <p>The client-side handler method reference ({@code ClientQuestState::apply*})
 * is safe to register from common code on a dedicated server: registering a
 * method reference only resolves the method's own class, it doesn't execute
 * the method body (which is the part that would touch client-only state) -
 * same pattern this codebase's own client-only payload handlers should
 * follow if more are added later.
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
    }

    private ModNetworking() {
    }
}
