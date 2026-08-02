package dev.vanillaplusplus.vppskills.network;

import dev.vanillaplusplus.vppskills.VppSkills;
import dev.vanillaplusplus.vppskills.client.ClientSkillTreeState;
import dev.vanillaplusplus.vppskills.server.ServerSkillEvents;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

/**
 * Registers this mod's two sync/request payloads:
 * {@link SkillProgressSyncPayload} (server -&gt; client, see that class for
 * why it's a single JSON-string payload rather than a fully typed stream
 * codec, same Phase A simplification {@code vppquests}' {@code ModNetworking}
 * already documented) and {@link SkillUnlockRequestPayload} (client -&gt;
 * server - the #163 phase-3 click-to-unlock request this class's own doc
 * previously flagged as not-yet-wired). Mirrors {@code vppquests}'
 * {@code ModNetworking} registration shape exactly (same
 * {@code RegisterPayloadHandlersEvent}/{@code PayloadRegistrar} pattern,
 * same protocol version string).
 *
 * <p>Both handler method references ({@code ClientSkillTreeState::applyProgress},
 * {@code ServerSkillEvents::handleUnlockRequest}) are safe to register from
 * common code on either dist for the same reason {@code vppquests}'
 * {@code ModNetworking} documents: registering a method reference only
 * resolves the method's own class, it doesn't execute the method body (so a
 * dedicated server never touches {@code ClientSkillTreeState}, and a client
 * never touches {@code ServerSkillEvents}, purely by virtue of which
 * direction each payload actually flows).
 *
 * <p><b>Login-sync + unlock handling now wired</b> (see
 * {@code server.ServerSkillEvents}) - this class's previous revision
 * documented both as deferred; #163 phase 3 closes that loop.
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

        registrar.playToServer(
                SkillUnlockRequestPayload.TYPE,
                SkillUnlockRequestPayload.STREAM_CODEC,
                (payload, context) -> context.enqueueWork(() -> ServerSkillEvents.handleUnlockRequest(payload, context.player())));
    }

    private ModNetworking() {
    }
}
