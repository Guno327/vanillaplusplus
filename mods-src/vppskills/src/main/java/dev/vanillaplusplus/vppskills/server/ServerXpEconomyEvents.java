package dev.vanillaplusplus.vppskills.server;

import dev.vanillaplusplus.vppskills.VppSkills;
import dev.vanillaplusplus.vppskills.data.ModAttachments;
import dev.vanillaplusplus.vppskills.data.SkillProgressAttachment;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.entity.player.PlayerXpEvent;

/**
 * The #163 economy phase's XP-source point grant: owner direction is
 * "1 skill point per vanilla XP level gained" (vanilla's own XP curve, no
 * bespoke rate - see this mod's phase-B brief). Ground-truthed via
 * {@code javap} against the resolved {@code neoforge-21.1.235-merged.jar}
 * (same technique {@link dev.vanillaplusplus.vppskills.reward.AttributeOperationTranslator}'s
 * class doc already used) rather than assumed from memory:
 * <ul>
 *   <li>{@code net.neoforged.neoforge.event.entity.player.PlayerXpEvent.LevelChange}
 *       is a concrete, cancellable event with a constructor
 *       {@code (Player, int)} and a getter/setter pair {@code getLevels()}/
 *       {@code setLevels(int)} for the level delta.</li>
 *   <li>{@code getEntity()} (inherited from {@code PlayerEvent}) returns the
 *       {@code Player} the level change happened to - overridden 3 times up
 *       the {@code LivingEvent}/{@code Event} hierarchy to narrow the return
 *       type, but {@code PlayerEvent}'s own {@code Player}-typed override is
 *       the one that resolves here.</li>
 * </ul>
 *
 * <p>Only POSITIVE deltas grant points - enchanting tables spend levels,
 * which fires this same event with a NEGATIVE {@code getLevels()}, and the
 * owner-approved economy must not claw back skill points for that (per the
 * phase-B brief). The delta-&gt;points decision itself is the pure,
 * event-object-free {@link #pointsForLevelDelta} so it's unit-testable
 * without booting the game - this class's only other job is wiring that
 * decision to the real attachment + resync, exactly like
 * {@code command.VppSkillsCommand}'s {@code grantpoints} debug command
 * already does.
 */
@EventBusSubscriber(modid = VppSkills.MODID)
public final class ServerXpEconomyEvents {

    @SubscribeEvent
    static void onPlayerLevelChange(PlayerXpEvent.LevelChange event) {
        int pointsToGrant = pointsForLevelDelta(event.getLevels());
        if (pointsToGrant <= 0) {
            return;
        }
        if (event.getEntity() instanceof ServerPlayer serverPlayer) {
            SkillProgressAttachment progress = serverPlayer.getData(ModAttachments.SKILL_PROGRESS);
            progress.grantPoints(pointsToGrant);
            ServerSkillEvents.syncToPlayer(serverPlayer);
        }
    }

    /**
     * Pure delta-&gt;points-to-grant decision, kept free of
     * {@code PlayerXpEvent} so it's directly unit-testable: a positive
     * {@code levelDelta} (levels gained) grants that many points 1:1;
     * zero or negative (enchanting spends levels) grants none.
     */
    static int pointsForLevelDelta(int levelDelta) {
        return Math.max(levelDelta, 0);
    }

    private ServerXpEconomyEvents() {
    }
}
