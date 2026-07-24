package dev.vanillaplusplus.vppintegration.network;

import dev.vanillaplusplus.vppintegration.VppIntegration;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.function.Consumer;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.network.ConfigurationTask;
import net.minecraft.server.network.ConfigurationTask.Type;
import net.minecraft.network.protocol.configuration.ServerConfigurationPacketListener;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.network.configuration.ICustomConfigurationTask;
import net.neoforged.neoforge.network.event.RegisterConfigurationTasksEvent;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.handling.IPayloadContext;

/**
 * GitHub issue #94 follow-up: "the warning [about a client/server pack
 * version mismatch] should appear before the crash from no mods. Check if
 * this is feasible."
 *
 * <h2>Feasibility finding (read before touching this class)</h2>
 * NOT reachable in general. When a client is missing a mod the server
 * requires outright (or has a different jar version of one), NeoForge
 * rejects the connection during its own FML mod-list handshake - this
 * happens before ANY mod's Java code runs for that connection, before the
 * CONFIGURATION protocol phase this class hooks even starts, and long
 * before {@code PlayerEvents.loggedIn} (see {@code
 * pack/kubejs/server_scripts/version_check.js}, which fires in the PLAY
 * phase, later still). No mod - including this one - can inject a message
 * into, or run any code ahead of, that handshake for a client that lacks
 * the mod in the first place. That case's only reachable warning remains
 * the server MOTD (pack/server.properties), visible in the multiplayer
 * server list BEFORE a connection is even attempted - already shipped
 * as GitHub issue #94's "Prong B".
 *
 * <p>What IS reachable, and what this class implements: a client that
 * DOES have the exact same mod list/versions as the server (so it clears
 * the FML handshake fine) but is running different pack CONTENT - a
 * config/KubeJS/data/quest revision bump that didn't require touching any
 * mod jar. That drift is invisible to NeoForge's own handshake (it only
 * compares mod ids + jar versions, not our pack/VERSION concept) and is
 * exactly the gap the existing KubeJS-based version_check.js closes today
 * - but only AFTER the player has already joined the PLAY phase and the
 * world has started streaming to them. This class closes the same gap
 * one phase earlier: NeoForge's CONFIGURATION phase
 * ({@link RegisterConfigurationTasksEvent}), which runs after the FML
 * handshake succeeds but strictly BEFORE PLAY starts - before any chunk/
 * entity/inventory data streams, so a mismatched client is disconnected
 * with a clear, custom message instead of ever being handed content that
 * could desync or throw downstream. The existing KubeJS chat/toast notice
 * is left in place as a defense-in-depth fallback (e.g. a dev sandbox that
 * hasn't baked {@code config/vppplusplus/pack_version.txt} yet, or a
 * connection where this gate no-ops for any reason below).
 *
 * <h2>How it works</h2>
 * <ul>
 *   <li>{@code scripts/version_kubejs.py}'s {@code render_config_version_file}
 *   bakes {@code pack/VERSION} into a plain-text file at build time -
 *   {@code config/vppplusplus/pack_version.txt} - written by BOTH
 *   {@code scripts/build_mrpack.py} (client .mrpack overrides) and
 *   {@code scripts/build_server.py} (server bundle), the same "bake at
 *   build time, don't commit" pattern already used for the KubeJS
 *   {@code generated_version.js} constant and for the same reason: {@code
 *   pack/VERSION} on disk in this repo is always one release behind the
 *   version actually being minted (see that script's own header comment).</li>
 *   <li>On the server, {@link #registerConfigurationTask} adds a
 *   configuration task that sends the server's own baked version to the
 *   client over {@link PackVersionPayload}, then immediately marks itself
 *   done - it does not wait for any reply, the CLIENT decides whether
 *   there's a mismatch (same "client compares" philosophy as the existing
 *   KubeJS script, for the same reason: the server doesn't need to learn
 *   the client's version to act, only the client needs to learn the
 *   server's).</li>
 *   <li>On the client, {@link #onClientReceived} compares that to its own
 *   baked version and, on a mismatch, calls {@link IPayloadContext#disconnect}
 *   right there in the CONFIGURATION phase - before PLAY, before any world
 *   data.</li>
 *   <li>The payload channel is registered {@code .optional()} (see
 *   {@link #registerPayloads}) so a peer that doesn't understand it (an
 *   old build from before this feature shipped) never fails the whole
 *   connection over its absence - this gate only ever adds a warning, it
 *   never breaks a connection that would otherwise have worked.</li>
 * </ul>
 */
public final class PackVersionGate {
    private static final Type CONFIG_TASK_TYPE =
            new Type(ResourceLocation.fromNamespaceAndPath(VppIntegration.MODID, "pack_version_check"));
    private static final String VPP_RELEASES_URL = "https://github.com/Guno327/vanillaplusplus/releases";

    private PackVersionGate() {}

    public static void registerPayloads(RegisterPayloadHandlersEvent event) {
        event.registrar("1")
                .optional() // absence on either side must never fail the connection - see class doc
                .configurationToClient(PackVersionPayload.TYPE, PackVersionPayload.STREAM_CODEC, PackVersionGate::onClientReceived);
    }

    public static void registerConfigurationTask(RegisterConfigurationTasksEvent event) {
        String serverVersion = readBakedVersion();
        if (serverVersion == null) return; // not a real release build (dev sandbox) - skip silently, never block
        event.register(new SendTask(event.getListener(), serverVersion));
    }

    private record SendTask(ServerConfigurationPacketListener listener, String version) implements ICustomConfigurationTask {
        @Override
        public Type type() {
            return CONFIG_TASK_TYPE;
        }

        @Override
        public void run(Consumer<CustomPacketPayload> sender) {
            if (listener.hasChannel(PackVersionPayload.TYPE)) {
                sender.accept(new PackVersionPayload(version));
            }
            // No reply needed either way - the client decides for itself and
            // disconnects itself on a mismatch (see onClientReceived). Never
            // block the configuration sequence waiting on that.
            listener.finishCurrentTask(CONFIG_TASK_TYPE);
        }
    }

    private static void onClientReceived(PackVersionPayload payload, IPayloadContext context) {
        String clientVersion = readBakedVersion();
        String serverVersion = payload.version();
        if (clientVersion == null || serverVersion == null || clientVersion.equals(serverVersion)) return;

        context.disconnect(Component.literal(
                "[Vanilla++] Version mismatch! This server is running v" + serverVersion
                        + ", you have v" + clientVersion + " installed.\n"
                        + "Download the matching client (v" + serverVersion + ") from " + VPP_RELEASES_URL));
    }

    /**
     * Reads {@code config/vppplusplus/pack_version.txt}, baked at build time
     * on both the client and server side (see class doc). Returns null (and
     * never throws) if the file is missing/unreadable/empty - a dev sandbox
     * run straight from {@code mods-src/} rather than a real .mrpack/server
     * bundle build, or any other unexpected state. This gate must fail OPEN:
     * a bug here must never be able to disconnect a player who would
     * otherwise have connected fine.
     */
    private static String readBakedVersion() {
        try {
            Path path = FMLPaths.CONFIGDIR.get().resolve("vppplusplus").resolve("pack_version.txt");
            if (!Files.isRegularFile(path)) return null;
            String version = Files.readString(path).strip();
            return version.isEmpty() ? null : version;
        } catch (IOException | RuntimeException e) {
            VppIntegration.LOGGER.warn("vppintegration: could not read config/vppplusplus/pack_version.txt, "
                    + "skipping the connection-time version gate for this connection", e);
            return null;
        }
    }
}
