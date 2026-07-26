package dev.vanillaplusplus.vppskills.server;

import dev.vanillaplusplus.vppskills.VppSkills;
import dev.vanillaplusplus.vppskills.data.ModAttachments;
import dev.vanillaplusplus.vppskills.data.SkillProgressAttachment;
import dev.vanillaplusplus.vppskills.network.SkillProgressSyncPayload;
import dev.vanillaplusplus.vppskills.network.SkillUnlockRequestPayload;
import dev.vanillaplusplus.vppskills.reward.AttributeModifierSpec;
import dev.vanillaplusplus.vppskills.reward.AttributeOperationTranslator;
import dev.vanillaplusplus.vppskills.reward.SkillAttributeApplier;
import dev.vanillaplusplus.vppskills.tree.SkillTreeCategory;
import dev.vanillaplusplus.vppskills.tree.SkillTreeNode;
import dev.vanillaplusplus.vppskills.unlock.SkillUnlockValidator;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Player;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.network.PacketDistributor;

import java.util.List;
import java.util.Optional;

/**
 * Server-side lifecycle wiring for the skill tree - the #163 phase-3
 * analogue of {@code vppquests}' {@code quest.ServerQuestEvents}: syncs a
 * player's {@code SkillProgressAttachment} to them on login (the hook
 * {@code network.ModNetworking}'s class doc explicitly deferred after
 * phase 2), and handles the click-to-unlock request payload
 * {@link SkillUnlockRequestPayload} registered there.
 *
 * <p><b>Never trusts the client's view.</b> {@link #handleUnlockRequest}
 * re-derives the category from {@link ServerSkillTreeState} (this mod's own
 * server-side copy of the tree, not anything the client asserted) and runs
 * the request through {@link SkillUnlockValidator#tryUnlock} - the same
 * pure, already-unit-tested decision+mutation helper phase 2 built - before
 * ever touching the player's {@link SkillProgressAttachment}. On success it
 * also applies the node's attribute reward(s) via
 * {@link AttributeOperationTranslator}/{@link SkillAttributeApplier} (the
 * reward-application seam phase 2 built but left unwired - see
 * {@link SkillAttributeApplier}'s class doc). Every request - accepted or
 * rejected - ends with a fresh {@link SkillProgressSyncPayload} back to the
 * requester, so a rejected request can never leave the client's mirror
 * showing something the server didn't actually do.
 */
@EventBusSubscriber(modid = VppSkills.MODID)
public final class ServerSkillEvents {

    @SubscribeEvent
    static void onPlayerLoggedIn(PlayerEvent.PlayerLoggedInEvent event) {
        if (event.getEntity() instanceof ServerPlayer serverPlayer) {
            syncToPlayer(serverPlayer);
        }
    }

    /** Pushes {@code player}'s current {@link SkillProgressAttachment} state to their own client. */
    public static void syncToPlayer(ServerPlayer player) {
        SkillProgressAttachment progress = player.getData(ModAttachments.SKILL_PROGRESS);
        PacketDistributor.sendToPlayer(player, new SkillProgressSyncPayload(progress.toJson()));
    }

    /**
     * Handles one {@link SkillUnlockRequestPayload} - called from
     * {@code network.ModNetworking}'s {@code playToServer} registration,
     * already on the server main thread (via {@code IPayloadContext#enqueueWork}).
     */
    public static void handleUnlockRequest(SkillUnlockRequestPayload payload, Player player) {
        if (!(player instanceof ServerPlayer serverPlayer)) {
            // Only a real server-side player can own an attachment/be unlocked for - anything
            // else (e.g. a stray call with a client-side Player) is not a request we can act on.
            return;
        }

        SkillTreeCategory category = ServerSkillTreeState.get().categories().get(payload.categoryId());
        if (category != null) {
            SkillProgressAttachment progress = serverPlayer.getData(ModAttachments.SKILL_PROGRESS);
            SkillUnlockValidator.Result result = SkillUnlockValidator.tryUnlock(category, payload.nodeId(), progress);
            if (result == SkillUnlockValidator.Result.OK) {
                applyNodeRewards(serverPlayer, category, payload.nodeId());
            } else {
                VppSkills.LOGGER.debug("vppskills: rejected unlock request from {} for {}/{}: {}",
                        serverPlayer.getGameProfile().getName(), payload.categoryId(), payload.nodeId(), result);
            }
        } else {
            VppSkills.LOGGER.warn("vppskills: unlock request from {} referenced unknown category {}",
                    serverPlayer.getGameProfile().getName(), payload.categoryId());
        }

        // Always resync, accepted or rejected, so the client's mirror can never drift
        // from what the server actually did (see this class's doc).
        syncToPlayer(serverPlayer);
    }

    private static void applyNodeRewards(ServerPlayer player, SkillTreeCategory category, String nodeId) {
        Optional<SkillTreeNode> node = category.nodes().stream().filter(n -> n.id().equals(nodeId)).findFirst();
        if (node.isEmpty() || node.get().rewards().isEmpty()) {
            return;
        }
        List<AttributeModifierSpec> specs = AttributeOperationTranslator.translate(nodeId, node.get().rewards());
        SkillAttributeApplier.apply(player, specs);
    }

    private ServerSkillEvents() {
    }
}
