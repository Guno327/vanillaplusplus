package dev.vanillaplusplus.vppskills.network;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import net.minecraft.core.RegistryAccess;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.neoforged.neoforge.network.connection.ConnectionType;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Byte round-trip test for {@link SkillUnlockRequestPayload#STREAM_CODEC},
 * per #163 phase-3's hard test requirement (a). Uses
 * {@link RegistryAccess#EMPTY} to construct the {@link RegistryFriendlyByteBuf}
 * this payload's codec type demands - safe here since the codec only ever
 * touches plain UTF-8 strings ({@code ByteBufCodecs#STRING_UTF8}), never any
 * actual registry lookup, so no real registry needs to be booted for this
 * test (ground-truthed: {@code RegistryFriendlyByteBuf}'s constructor only
 * needs a {@link RegistryAccess} reference to satisfy its type, not to
 * resolve anything, for a payload shaped like this one). Uses the 3-arg
 * {@code (ByteBuf, RegistryAccess, ConnectionType)} constructor rather than
 * the 2-arg one - {@code javap} against the resolved jar showed the 2-arg
 * overload carries {@code @Deprecated} - {@link ConnectionType#OTHER} is an
 * arbitrary but valid choice since this test never inspects connection type.
 */
class SkillUnlockRequestPayloadTest {

    @Test
    void encodeThenDecodeRoundTripsCategoryAndNodeIds() {
        SkillUnlockRequestPayload original = new SkillUnlockRequestPayload("adventurer", "max_health");

        ByteBuf buf = Unpooled.buffer();
        RegistryFriendlyByteBuf writeBuf = new RegistryFriendlyByteBuf(buf, RegistryAccess.EMPTY, ConnectionType.OTHER);
        SkillUnlockRequestPayload.STREAM_CODEC.encode(writeBuf, original);

        RegistryFriendlyByteBuf readBuf = new RegistryFriendlyByteBuf(buf, RegistryAccess.EMPTY, ConnectionType.OTHER);
        SkillUnlockRequestPayload decoded = SkillUnlockRequestPayload.STREAM_CODEC.decode(readBuf);

        assertEquals(original.categoryId(), decoded.categoryId());
        assertEquals(original.nodeId(), decoded.nodeId());
    }

    @Test
    void payloadTypeIsRegisteredUnderVppskillsNamespace() {
        assertEquals("vppskills", SkillUnlockRequestPayload.TYPE.id().getNamespace());
        assertEquals("skill_unlock_request", SkillUnlockRequestPayload.TYPE.id().getPath());
    }
}
