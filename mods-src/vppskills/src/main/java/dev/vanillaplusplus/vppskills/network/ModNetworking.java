package dev.vanillaplusplus.vppskills.network;

import dev.vanillaplusplus.vppskills.VppSkills;
import dev.vanillaplusplus.vppskills.client.ClientSkillTreeState;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

/**
 * Registers this mod's one sync payload
 * ({@link SkillProgressSyncPayload} - see that class for why it's a single
 * JSON-string payload rather than a fully typed stream codec, same Phase A
 * simplification {@code vppquests}' {@code ModNetworking} already
 * documented). Mirrors that class's registration shape exactly (same
 * {@code RegisterPayloadHandlersEvent}/{@code PayloadRegistrar} pattern,
 * same protocol version string).
 *
 * <p>The client-side handler method reference
 * ({@code ClientSkillTreeState::applyProgress}) is safe to register from
 * common code on a dedicated server for the same reason
 * {@code vppquests}' {@code ModNetworking} documents: registering a method
 * reference only resolves the method's own class, it doesn't execute the
 * method body.
 *
 * <p><b>Not wired to a send-on-login/send-on-change event yet.</b> #163
 * phase-2 scope is "server-&gt;client mirror + registration" only; a future
 * phase adds the {@code ServerPlayer} login/attachment-change hook that
 * actually calls {@code PacketDistributor.sendToPlayer(player, new
 * SkillProgressSyncPayload(...))} (same shape as {@code vppquests}'
 * {@code ServerQuestEvents#syncAllToPlayer}), once click-to-unlock exists on
 * the server side for this payload to actually report on.
 */
@EventBusSubscriber(modid = VppSkills.MODID)
public final class ModNetworking {

    @SubscribeEvent
    static void register(RegisterPayloadHandlersEvent event) {
        PayloadRegistrar registrar = event.registrar("1");

        registrar.playToClient(
                SkillProgressSyncPayload.TYPE,
                SkillProgressSyncPayload.STREAM_CODEC,
                (payload, context) -> context.enqueueWork(() -> ClientSkillTreeState.applyProgress(payload.progressJson())));
    }

    private ModNetworking() {
    }
}
