package dev.vanillaplusplus.vppskills.network;

import dev.vanillaplusplus.vppskills.VppSkills;

import java.nio.charset.StandardCharsets;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;

/**
 * Server -&gt; client: the receiving player's own
 * {@code SkillProgressAttachment} state (unlocked node ids + available/spent
 * points), gson-serialized - the #163 phase-2 analogue of {@code vppquests}'
 * {@code QuestProgressSyncPayload}, registered the same way (see
 * {@link ModNetworking}) and applied client-side into
 * {@code ClientSkillTreeState} the same way {@code QuestProgressSyncPayload}
 * feeds {@code ClientQuestState}.
 *
 * <p>Unlike {@code QuestProgressSyncPayload} (which uses a plain
 * length-prefixed UTF string), this payload carries its JSON as a
 * length-prefixed UTF-8 <em>byte array</em> ({@code writeByteArray}/
 * {@code readByteArray}) up front - the same fix {@code vppquests}'
 * {@code QuestDefinitionsSyncPayload} needed after GitHub #156 (a
 * ~36.8k-char blob tripped {@code writeUtf}'s 32767-CHARACTER cap, not a
 * byte cap, and kicked every joining client with "String too big"). This
 * pack's real tree is 791 nodes (GitHub #116); a player who has unlocked a
 * large fraction of them could plausibly produce a JSON blob in that same
 * size class, so this payload is built byte-array-safe from the start
 * rather than waiting to hit the identical bug a second time.
 */
public record SkillProgressSyncPayload(String progressJson) implements CustomPacketPayload {

    public static final Type<SkillProgressSyncPayload> TYPE =
            new Type<>(ResourceLocation.fromNamespaceAndPath(VppSkills.MODID, "skill_progress_sync"));

    public static final StreamCodec<RegistryFriendlyByteBuf, SkillProgressSyncPayload> STREAM_CODEC =
            new StreamCodec<>() {
                @Override
                public SkillProgressSyncPayload decode(RegistryFriendlyByteBuf buf) {
                    return new SkillProgressSyncPayload(new String(buf.readByteArray(), StandardCharsets.UTF_8));
                }

                @Override
                public void encode(RegistryFriendlyByteBuf buf, SkillProgressSyncPayload payload) {
                    buf.writeByteArray(payload.progressJson().getBytes(StandardCharsets.UTF_8));
                }
            };

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
