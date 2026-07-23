package dev.vanillaplusplus.vppquests.network;

import dev.vanillaplusplus.vppquests.VppQuests;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;

/**
 * Server -> client: the receiving player's own {@code QuestProgressAttachment}
 * state (completed quest ids + task progress counters), gson-serialized -
 * same "one JSON round-trip, not per-field stream codecs yet" rationale as
 * {@link QuestDefinitionsSyncPayload}. Sent on login and whenever the
 * server mutates that player's attachment, so the client-side GUI/HUD can
 * render progress without a server round-trip per frame.
 */
public record QuestProgressSyncPayload(String progressJson) implements CustomPacketPayload {

    public static final Type<QuestProgressSyncPayload> TYPE =
            new Type<>(ResourceLocation.fromNamespaceAndPath(VppQuests.MODID, "quest_progress_sync"));

    public static final StreamCodec<RegistryFriendlyByteBuf, QuestProgressSyncPayload> STREAM_CODEC =
            StreamCodec.composite(
                    ByteBufCodecs.STRING_UTF8, QuestProgressSyncPayload::progressJson,
                    QuestProgressSyncPayload::new);

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
