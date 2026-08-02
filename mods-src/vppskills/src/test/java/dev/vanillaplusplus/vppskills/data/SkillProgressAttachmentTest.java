package dev.vanillaplusplus.vppskills.data;

import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for {@link SkillProgressAttachment}'s
 * {@code toJson}/{@code fromJson} round-trip (the same Codec-via-JsonOps
 * technique the network sync payload and the NBT attachment serialization
 * both rely on - see that class's doc), per #163 phase-2's hard test
 * requirement (c).
 */
class SkillProgressAttachmentTest {

    @Test
    void roundTripPreservesUnlockedNodesAndPoints() {
        SkillProgressAttachment original = new SkillProgressAttachment();
        original.grantPoints(10);
        original.unlock("root", 1);
        original.unlock("mid", 2);

        SkillProgressAttachment restored = SkillProgressAttachment.fromJson(original.toJson());

        assertEquals(original.unlockedNodeIds(), restored.unlockedNodeIds());
        assertEquals(original.availablePoints(), restored.availablePoints());
        assertEquals(original.spentPoints(), restored.spentPoints());
        assertTrue(restored.isUnlocked("root"));
        assertTrue(restored.isUnlocked("mid"));
    }

    @Test
    void roundTripOfFreshAttachmentIsEmpty() {
        SkillProgressAttachment original = new SkillProgressAttachment();

        SkillProgressAttachment restored = SkillProgressAttachment.fromJson(original.toJson());

        assertTrue(restored.unlockedNodeIds().isEmpty());
        assertEquals(0, restored.availablePoints());
        assertEquals(0, restored.spentPoints());
    }

    @Test
    void unlockDebitsAvailablePointsAndCreditsSpentPoints() {
        SkillProgressAttachment attachment = new SkillProgressAttachment();
        attachment.grantPoints(5);

        attachment.unlock("root", 2);

        assertEquals(3, attachment.availablePoints());
        assertEquals(2, attachment.spentPoints());
        assertTrue(attachment.isUnlocked("root"));
    }

    @Test
    void respecRefundsPointsAndRemovesNode() {
        SkillProgressAttachment attachment = new SkillProgressAttachment();
        attachment.grantPoints(5);
        attachment.unlock("root", 2);

        attachment.respec("root", 2);

        assertEquals(5, attachment.availablePoints());
        assertEquals(0, attachment.spentPoints());
        assertTrue(attachment.unlockedNodeIds().isEmpty());
    }

    @Test
    void malformedJsonFallsBackToEmptyAttachmentRatherThanThrowing() {
        SkillProgressAttachment restored = SkillProgressAttachment.fromJson("{\"not\":\"valid\"}");

        assertTrue(restored.unlockedNodeIds().isEmpty());
        assertEquals(0, restored.availablePoints());
        assertEquals(0, restored.spentPoints());
    }

    @Test
    void fullRespecClearsNodesMovesSpentToAvailableAndReturnsClearedIds() {
        SkillProgressAttachment attachment = new SkillProgressAttachment();
        attachment.grantPoints(10);
        attachment.unlock("root", 1);
        attachment.unlock("mid", 2);

        Set<String> clearedNodeIds = attachment.fullRespec();

        assertEquals(Set.of("root", "mid"), clearedNodeIds);
        assertTrue(attachment.unlockedNodeIds().isEmpty());
        assertEquals(10, attachment.availablePoints());
        assertEquals(0, attachment.spentPoints());
    }

    @Test
    void fullRespecOnFreshAttachmentIsANoOp() {
        SkillProgressAttachment attachment = new SkillProgressAttachment();
        attachment.grantPoints(3);

        Set<String> clearedNodeIds = attachment.fullRespec();

        assertTrue(clearedNodeIds.isEmpty());
        assertEquals(3, attachment.availablePoints());
        assertEquals(0, attachment.spentPoints());
    }

    @Test
    void freeRespecAvailableDefaultsToTrueAndConsumeFlipsItOnce() {
        SkillProgressAttachment attachment = new SkillProgressAttachment();

        assertTrue(attachment.freeRespecAvailable());
        assertTrue(attachment.consumeFreeRespec());
        assertFalse(attachment.freeRespecAvailable());
        assertFalse(attachment.consumeFreeRespec());
        assertFalse(attachment.freeRespecAvailable());
    }

    @Test
    void freeRespecAvailableSurvivesJsonRoundTrip() {
        SkillProgressAttachment original = new SkillProgressAttachment();
        original.consumeFreeRespec();

        SkillProgressAttachment restored = SkillProgressAttachment.fromJson(original.toJson());

        assertFalse(restored.freeRespecAvailable());
    }

    @Test
    void legacyJsonMissingFreeRespecFieldDecodesToTrue() {
        // Pre-economy-phase save data has no "freeRespecAvailable" key at all - must decode
        // to true (existing players haven't used their free respec yet), not fail to decode.
        SkillProgressAttachment restored = SkillProgressAttachment.fromJson(
                "{\"unlockedNodes\":[],\"availablePoints\":0,\"spentPoints\":0}");

        assertTrue(restored.freeRespecAvailable());
    }
}
