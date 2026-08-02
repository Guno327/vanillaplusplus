package dev.vanillaplusplus.vppskills.server;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Unit tests for {@link ServerXpEconomyEvents#pointsForLevelDelta}, the pure
 * decision behind the #163 economy phase's "1 skill point per vanilla XP
 * level gained" rule - kept free of the real
 * {@code net.neoforged.neoforge.event.entity.player.PlayerXpEvent.LevelChange}
 * event object specifically so it's testable here without booting the game
 * (see that class's doc).
 */
class ServerXpEconomyEventsTest {

    @Test
    void positiveDeltaGrantsThatManyPoints() {
        assertEquals(1, ServerXpEconomyEvents.pointsForLevelDelta(1));
        assertEquals(5, ServerXpEconomyEvents.pointsForLevelDelta(5));
    }

    @Test
    void zeroDeltaGrantsNoPoints() {
        assertEquals(0, ServerXpEconomyEvents.pointsForLevelDelta(0));
    }

    @Test
    void negativeDeltaGrantsNoPoints() {
        // Enchanting tables spend levels, firing this same event with a negative
        // delta - must never claw back skill points (see class doc).
        assertEquals(0, ServerXpEconomyEvents.pointsForLevelDelta(-1));
        assertEquals(0, ServerXpEconomyEvents.pointsForLevelDelta(-30));
    }
}
