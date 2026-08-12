package dev.vanillaplusplus.vppquests.quest;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * Regression tests for GitHub #164 item&nbsp;5: every quest's {@code xp}
 * reward carries a skill-category the pack cares about, but
 * {@link QuestRewardBridge} used to have no seam to route it anywhere other
 * than plain vanilla XP, silently discarding the category. These pin the
 * granter seam: a registered granter is used instead of the vanilla default,
 * and a throwing granter is swallowed and the reward re-granted as vanilla
 * XP rather than crashing the quest tick or shorting the player.
 *
 * <p><b>Why these use {@code assertThrows(NullPointerException.class)} to
 * observe the vanilla fallback.</b> The vanilla default calls
 * {@code ServerPlayer#giveExperiencePoints(int)}, an instance method on a
 * live-server class this test cannot construct without a mocking library
 * (forbidden by this repo's test conventions - see vppskills' existing
 * tests, none of which mock Minecraft classes either). Passing {@code null}
 * as the player turns "the vanilla path was reached" into an observable
 * {@link NullPointerException} instead of a silent no-op: when a custom
 * granter is registered it never touches the player argument (it only
 * records it), so no exception happens; when the code falls through to
 * {@code VANILLA} (no granter registered, or the registered granter threw),
 * {@code null.giveExperiencePoints(...)} throws. The NPE is also
 * distinguishable from the granter's <em>own</em> exception (a
 * {@code RuntimeException} with a distinct message) in the swallow test,
 * proving the original exception was actually caught and not left to
 * propagate.
 *
 * <p>{@link QuestRewardBridge}'s granter is held in a static field, so every
 * test resets it in {@link #resetGranter()} to avoid leaking state between
 * tests.
 */
class QuestRewardBridgeTest {

    @AfterEach
    void resetGranter() {
        QuestRewardBridge.setSkillXpGranter(null);
    }

    @Test
    void registeredGranterReceivesCallInsteadOfVanillaDefault() {
        int[] captured = new int[1];
        String[] capturedCategory = new String[1];
        QuestRewardBridge.setSkillXpGranter((player, category, amount) -> {
            capturedCategory[0] = category;
            captured[0] = amount;
        });

        QuestRewardBridge.grantSkillXp(null, "adventurer", 50);

        assertEquals("adventurer", capturedCategory[0]);
        assertEquals(50, captured[0]);
    }

    @Test
    void noGranterRegisteredFallsThroughToVanillaExperience() {
        // No granter registered - grantSkillXp must attempt the vanilla path,
        // which for a null player surfaces as an NPE (see class doc).
        assertThrows(NullPointerException.class,
                () -> QuestRewardBridge.grantSkillXp(null, "adventurer", 10));
    }

    @Test
    void throwingGranterIsSwallowedAndFallsBackToVanilla() {
        QuestRewardBridge.setSkillXpGranter((player, category, amount) -> {
            throw new RuntimeException("bridge blew up");
        });

        // If the granter's own RuntimeException("bridge blew up") propagated
        // unswallowed, this would throw *that* exception, not an NPE.
        // Getting an NPE instead proves it was caught and vanilla fallback
        // attempted.
        NullPointerException thrown = assertThrows(NullPointerException.class,
                () -> QuestRewardBridge.grantSkillXp(null, "adventurer", 10));

        assertEquals(NullPointerException.class, thrown.getClass());
    }

    @Test
    void settingNullGranterResetsToVanillaDefault() {
        QuestRewardBridge.setSkillXpGranter((player, category, amount) -> {
            // registered granter would succeed silently; never invoked below.
        });

        QuestRewardBridge.setSkillXpGranter(null);

        assertThrows(NullPointerException.class,
                () -> QuestRewardBridge.grantSkillXp(null, "adventurer", 10));
    }
}
