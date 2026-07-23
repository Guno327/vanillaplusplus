package dev.vanillaplusplus.vppquests.network;

import dev.vanillaplusplus.vppquests.VppQuests;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;

/**
 * Server -> client: the full quest/chapter registry, gson-serialized as one
 * JSON string blob rather than a fully typed nested {@code StreamCodec} per
 * quest field. Deliberate Phase A simplification: the data model
 * ({@link dev.vanillaplusplus.vppquests.quest.Quest}/{@link
 * dev.vanillaplusplus.vppquests.quest.QuestTask}/{@link
 * dev.vanillaplusplus.vppquests.quest.QuestReward}) is still evolving
 * (Phase D's questline rebuild is expected to touch it), so a hand-rolled
 * per-field {@code StreamCodec} would need re-deriving every time that
 * schema changes; re-using the same Gson round-trip
 * {@link dev.vanillaplusplus.vppquests.quest.Quest#fromJson} already
 * implements keeps client and server parsing on exactly one code path. A
 * later phase can replace this with real per-field stream codecs once the
 * schema stabilizes post-rebuild, without changing any other class's
 * public API.
 *
 * <p>Sent to a client on login and whenever the server's datapacks reload
 * (see {@code QuestReloadListener}) so the client-side quest-map GUI has a
 * definitions mirror to render against without round-tripping to the
 * server per frame, per DESIGN.md's #109 design-proposal section.
 */
public record QuestDefinitionsSyncPayload(String questsJson) implements CustomPacketPayload {

    public static final Type<QuestDefinitionsSyncPayload> TYPE =
            new Type<>(ResourceLocation.fromNamespaceAndPath(VppQuests.MODID, "quest_definitions_sync"));

    public static final StreamCodec<RegistryFriendlyByteBuf, QuestDefinitionsSyncPayload> STREAM_CODEC =
            StreamCodec.composite(
                    ByteBufCodecs.STRING_UTF8, QuestDefinitionsSyncPayload::questsJson,
                    QuestDefinitionsSyncPayload::new);

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
