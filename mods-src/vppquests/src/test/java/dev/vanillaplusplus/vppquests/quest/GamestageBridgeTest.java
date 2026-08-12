package dev.vanillaplusplus.vppquests.quest;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Regression tests for GitHub #166: with no resolver wired,
 * {@link GamestageBridge#hasStage} unconditionally returned false, so every
 * chapter's single {@code gamestage} "enter" task could never complete, which
 * (since every other quest in a chapter depends on its enter quest) hard-
 * locked all 9 chapters. These pin the resolver seam: safe default, pass-
 * through of a registered resolver's result, and swallowing a throwing
 * resolver to the safe default rather than propagating it into the quest
 * tick.
 *
 * <p>{@link GamestageBridge}'s resolver is held in a static field, so every
 * test resets it in {@link #resetResolver()} to avoid leaking state between
 * tests (and between this class and any other test that might register one).
 * {@code player} is passed as {@code null} throughout since none of the
 * resolvers registered here dereference it - {@link GamestageBridge} only
 * ever forwards the reference, never touches it itself.
 */
class GamestageBridgeTest {

    @AfterEach
    void resetResolver() {
        GamestageBridge.setResolver(null);
    }

    @Test
    void defaultResolverReturnsFalseWhenNoneRegistered() {
        assertFalse(GamestageBridge.hasStage(null, "stone_age"));
    }

    @Test
    void registeredResolverResultPassesThrough() {
        GamestageBridge.setResolver((player, stage) -> stage.equals("stone_age"));

        assertTrue(GamestageBridge.hasStage(null, "stone_age"));
        assertFalse(GamestageBridge.hasStage(null, "iron_age"));
    }

    @Test
    void throwingResolverIsSwallowedToFalse() {
        GamestageBridge.setResolver((player, stage) -> {
            throw new RuntimeException("bridge blew up");
        });

        assertFalse(GamestageBridge.hasStage(null, "stone_age"));
    }

    @Test
    void settingNullResolverResetsToDefault() {
        GamestageBridge.setResolver((player, stage) -> true);
        assertTrue(GamestageBridge.hasStage(null, "stone_age"));

        GamestageBridge.setResolver(null);

        assertFalse(GamestageBridge.hasStage(null, "stone_age"));
    }
}
