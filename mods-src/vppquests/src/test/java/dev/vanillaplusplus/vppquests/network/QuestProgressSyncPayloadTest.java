package dev.vanillaplusplus.vppquests.network;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import net.minecraft.core.RegistryAccess;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.neoforged.neoforge.network.connection.ConnectionType;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Byte round-trip test for {@link QuestProgressSyncPayload#STREAM_CODEC}, the
 * per-player progress counterpart to {@link QuestDefinitionsSyncPayloadTest}.
 * Unlike the definitions payload, this one already used
 * {@code ByteBufCodecs.STRING_UTF8} rather than a hand-rolled codec at the
 * time of #156 - included here per #194's task list for completeness/parity,
 * not because it was itself the #156 regression.
 */
class QuestProgressSyncPayloadTest {

    @Test
    void encodeThenDecodeRoundTripsProgressJson() {
        QuestProgressSyncPayload original = new QuestProgressSyncPayload(
                "{\"completed\":[\"vppquests:ch1/enter\"],\"taskProgress\":{\"vppquests:ch1/enter#0\":1}}");

        ByteBuf buf = Unpooled.buffer();
        RegistryFriendlyByteBuf writeBuf = new RegistryFriendlyByteBuf(buf, RegistryAccess.EMPTY, ConnectionType.OTHER);
        QuestProgressSyncPayload.STREAM_CODEC.encode(writeBuf, original);

        RegistryFriendlyByteBuf readBuf = new RegistryFriendlyByteBuf(buf, RegistryAccess.EMPTY, ConnectionType.OTHER);
        QuestProgressSyncPayload decoded = QuestProgressSyncPayload.STREAM_CODEC.decode(readBuf);

        assertEquals(original.progressJson(), decoded.progressJson());
    }

    @Test
    void encodeThenDecodeRoundTripsEmptyProgressJson() {
        QuestProgressSyncPayload original = new QuestProgressSyncPayload("{\"completed\":[],\"taskProgress\":{}}");

        ByteBuf buf = Unpooled.buffer();
        RegistryFriendlyByteBuf writeBuf = new RegistryFriendlyByteBuf(buf, RegistryAccess.EMPTY, ConnectionType.OTHER);
        QuestProgressSyncPayload.STREAM_CODEC.encode(writeBuf, original);

        RegistryFriendlyByteBuf readBuf = new RegistryFriendlyByteBuf(buf, RegistryAccess.EMPTY, ConnectionType.OTHER);
        QuestProgressSyncPayload decoded = QuestProgressSyncPayload.STREAM_CODEC.decode(readBuf);

        assertEquals(original.progressJson(), decoded.progressJson());
    }

    @Test
    void payloadTypeIsRegisteredUnderVppquestsNamespace() {
        assertEquals("vppquests", QuestProgressSyncPayload.TYPE.id().getNamespace());
        assertEquals("quest_progress_sync", QuestProgressSyncPayload.TYPE.id().getPath());
    }
}
