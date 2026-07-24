package dev.vanillaplusplus.vppquests.network;

import dev.vanillaplusplus.vppquests.VppQuests;
import java.nio.charset.StandardCharsets;
import net.minecraft.network.RegistryFriendlyByteBuf;
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

    /**
     * The full quest registry JSON routinely exceeds {@code writeUtf}'s 32767
     * character cap (see #156: a ~36.8k-char blob kicked every joining client
     * with "String too big"), so the JSON is carried as a length-prefixed
     * UTF-8 <em>byte array</em> rather than a length-prefixed UTF string. This
     * is a clean symmetric swap - {@code writeByteArray}/{@code readByteArray}
     * on the two sides - that keeps the same single-JSON-blob wire shape while
     * lifting the char cap to the custom-payload byte budget.
     */
    public static final StreamCodec<RegistryFriendlyByteBuf, QuestDefinitionsSyncPayload> STREAM_CODEC =
            new StreamCodec<>() {
                @Override
                public QuestDefinitionsSyncPayload decode(RegistryFriendlyByteBuf buf) {
                    return new QuestDefinitionsSyncPayload(
                            new String(buf.readByteArray(), StandardCharsets.UTF_8));
                }

                @Override
                public void encode(RegistryFriendlyByteBuf buf, QuestDefinitionsSyncPayload payload) {
                    buf.writeByteArray(payload.questsJson().getBytes(StandardCharsets.UTF_8));
                }
            };

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
