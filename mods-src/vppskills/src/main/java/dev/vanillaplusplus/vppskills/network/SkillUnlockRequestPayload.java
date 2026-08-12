package dev.vanillaplusplus.vppskills.network;

import dev.vanillaplusplus.vppskills.VppSkills;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;

/**
 * Client -&gt; server: "the requesting player wants to unlock this node" - the
 * #163 phase-3 client-half of the click-to-unlock loop {@code ModNetworking}'s
 * class doc explicitly left un-wired after phase 2. Carries just the category
 * id + node id; the server is the sole authority on whether the request is
 * legal ({@code unlock.SkillUnlockValidator#tryUnlock}, invoked by
 * {@code server.ServerSkillEvents#handleUnlockRequest}) - this payload itself
 * makes no claim about affordability/adjacency, it is only ever a request.
 *
 * <p>Unlike {@link SkillProgressSyncPayload} (which needed the
 * byte-array-safe encoding because a full progress blob can be large - see
 * that class's doc), category/node ids are short, bounded strings from this
 * pack's own tree data, so a plain {@code ByteBufCodecs.STRING_UTF8}
 * composite (same technique {@code vppquests}' {@code QuestProgressSyncPayload}
 * uses for its own short string) is the right fit here - no risk of tripping
 * {@code writeUtf}'s 32767-character cap.
 */
public record SkillUnlockRequestPayload(String categoryId, String nodeId) implements CustomPacketPayload {

    public static final Type<SkillUnlockRequestPayload> TYPE =
            new Type<>(ResourceLocation.fromNamespaceAndPath(VppSkills.MODID, "skill_unlock_request"));

    public static final StreamCodec<RegistryFriendlyByteBuf, SkillUnlockRequestPayload> STREAM_CODEC =
            StreamCodec.composite(
                    ByteBufCodecs.STRING_UTF8, SkillUnlockRequestPayload::categoryId,
                    ByteBufCodecs.STRING_UTF8, SkillUnlockRequestPayload::nodeId,
                    SkillUnlockRequestPayload::new);

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
