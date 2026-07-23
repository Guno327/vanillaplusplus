package dev.vanillaplusplus.vppintegration.network;

import dev.vanillaplusplus.vppintegration.VppIntegration;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;

/**
 * Carries the sending side's baked Vanilla++ pack version (from {@code
 * pack/VERSION}, see {@link PackVersionGate#readBakedVersion()}) over the
 * NeoForge CONFIGURATION protocol phase - i.e. after a client has already
 * passed NeoForge's own mod-list handshake (same mod ids/jar versions on
 * both sides) but strictly before it joins the PLAY phase / world.
 *
 * <p>See {@link PackVersionGate} for the full design writeup (GitHub issue
 * #94's "before the crash" follow-up) and exactly which mismatch class this
 * covers vs. cannot cover.
 */
public record PackVersionPayload(String version) implements CustomPacketPayload {
    public static final Type<PackVersionPayload> TYPE =
            new Type<>(ResourceLocation.fromNamespaceAndPath(VppIntegration.MODID, "pack_version"));

    // 64 chars is generous headroom over anything pack/VERSION will ever hold
    // (semver-ish strings like "0.5.2" or "0.5.2-rc1").
    public static final StreamCodec<FriendlyByteBuf, PackVersionPayload> STREAM_CODEC = StreamCodec.composite(
            ByteBufCodecs.stringUtf8(64), PackVersionPayload::version,
            PackVersionPayload::new);

    @Override
    public Type<PackVersionPayload> type() {
        return TYPE;
    }
}
