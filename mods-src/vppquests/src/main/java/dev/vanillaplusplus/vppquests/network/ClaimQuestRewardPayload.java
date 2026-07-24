package dev.vanillaplusplus.vppquests.network;

import dev.vanillaplusplus.vppquests.VppQuests;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;

/**
 * Client -> server: "I hit Claim on this quest, please grant its rewards."
 * GitHub #164 item 5's claim-on-hand-in system - the client sends only the
 * quest id it wants; it never carries the rewards themselves or asserts
 * completion, because the client is never trusted for the grant. The server
 * handler ({@code ModNetworking}) re-validates the quest is actually complete
 * and not already claimed against the player's own server-side
 * {@code QuestProgressAttachment} (see {@code QuestProgressTracker#claimReward})
 * before granting anything - a forged/replayed packet for an incomplete or
 * already-claimed quest is simply a no-op.
 */
public record ClaimQuestRewardPayload(ResourceLocation questId) implements CustomPacketPayload {

    public static final Type<ClaimQuestRewardPayload> TYPE =
            new Type<>(ResourceLocation.fromNamespaceAndPath(VppQuests.MODID, "claim_quest_reward"));

    public static final StreamCodec<RegistryFriendlyByteBuf, ClaimQuestRewardPayload> STREAM_CODEC =
            StreamCodec.composite(
                    ResourceLocation.STREAM_CODEC, ClaimQuestRewardPayload::questId,
                    ClaimQuestRewardPayload::new);

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
