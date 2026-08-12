package dev.vanillaplusplus.vppquests.network;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import net.minecraft.core.RegistryAccess;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.neoforged.neoforge.network.connection.ConnectionType;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Byte round-trip test for {@link QuestDefinitionsSyncPayload#STREAM_CODEC},
 * pinning GitHub #156: a ~36.8k-character quest-registry JSON blob kicked
 * every joining client with "String too big (was X, max 32767)" when the
 * codec used {@code ByteBufCodecs.STRING_UTF8} (which wraps
 * {@code ByteBuf#writeUtf}, capped at 32767 <em>characters</em>). The fix
 * moved the wire format to a length-prefixed UTF-8 <em>byte array</em>
 * ({@code writeByteArray}/{@code readByteArray}), which has no such cap.
 *
 * <p>Deliberately exercises a payload <em>larger</em> than 32767 characters -
 * a small string round-trips fine on the broken {@code writeUtf}-based code
 * too, so it would never have caught #156. See step 4 of the #194 task: this
 * is the test that was red-canaried against the pre-fix {@code writeUtf}
 * implementation to confirm it actually fails there.
 *
 * <p>Constructs the {@link RegistryFriendlyByteBuf} directly with
 * {@link RegistryAccess#EMPTY} and {@link ConnectionType#OTHER}, same as
 * {@code vppskills}'s {@code SkillUnlockRequestPayloadTest} - safe here since
 * this codec only ever touches a raw byte array, never any registry lookup.
 */
class QuestDefinitionsSyncPayloadTest {

    @Test
    void encodeThenDecodeRoundTripsOversizedJsonPastTheWriteUtfCharCap() {
        // 32767 is ByteBuf#writeUtf's max-character cap (the exact bug in #156);
        // pad comfortably past it so a writeUtf-based codec would throw here.
        String hugeJson = "{\"quests\":[" + "\"x\",".repeat(10_000) + "\"end\"]}";
        assertTrue(hugeJson.length() > 32767, "fixture must exceed writeUtf's 32767-char cap");

        QuestDefinitionsSyncPayload original = new QuestDefinitionsSyncPayload(hugeJson);

        ByteBuf buf = Unpooled.buffer();
        RegistryFriendlyByteBuf writeBuf = new RegistryFriendlyByteBuf(buf, RegistryAccess.EMPTY, ConnectionType.OTHER);
        QuestDefinitionsSyncPayload.STREAM_CODEC.encode(writeBuf, original);

        RegistryFriendlyByteBuf readBuf = new RegistryFriendlyByteBuf(buf, RegistryAccess.EMPTY, ConnectionType.OTHER);
        QuestDefinitionsSyncPayload decoded = QuestDefinitionsSyncPayload.STREAM_CODEC.decode(readBuf);

        assertEquals(original.questsJson(), decoded.questsJson());
        assertEquals(original.questsJson().length(), decoded.questsJson().length());
    }

    @Test
    void encodeThenDecodeRoundTripsSmallJson() {
        QuestDefinitionsSyncPayload original = new QuestDefinitionsSyncPayload("{\"quests\":[]}");

        ByteBuf buf = Unpooled.buffer();
        RegistryFriendlyByteBuf writeBuf = new RegistryFriendlyByteBuf(buf, RegistryAccess.EMPTY, ConnectionType.OTHER);
        QuestDefinitionsSyncPayload.STREAM_CODEC.encode(writeBuf, original);

        RegistryFriendlyByteBuf readBuf = new RegistryFriendlyByteBuf(buf, RegistryAccess.EMPTY, ConnectionType.OTHER);
        QuestDefinitionsSyncPayload decoded = QuestDefinitionsSyncPayload.STREAM_CODEC.decode(readBuf);

        assertEquals(original.questsJson(), decoded.questsJson());
    }

    @Test
    void payloadTypeIsRegisteredUnderVppquestsNamespace() {
        assertEquals("vppquests", QuestDefinitionsSyncPayload.TYPE.id().getNamespace());
        assertEquals("quest_definitions_sync", QuestDefinitionsSyncPayload.TYPE.id().getPath());
    }
}
