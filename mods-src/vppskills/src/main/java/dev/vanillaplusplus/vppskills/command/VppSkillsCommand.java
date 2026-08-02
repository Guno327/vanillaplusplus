package dev.vanillaplusplus.vppskills.command;

import com.mojang.brigadier.arguments.IntegerArgumentType;
import dev.vanillaplusplus.vppskills.VppSkills;
import dev.vanillaplusplus.vppskills.data.ModAttachments;
import dev.vanillaplusplus.vppskills.data.SkillProgressAttachment;
import dev.vanillaplusplus.vppskills.reward.SkillAttributeApplier;
import dev.vanillaplusplus.vppskills.server.ServerSkillEvents;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

import java.util.Set;

/**
 * {@code /vppskills grantpoints <n>} - a permission-gated
 * ({@code hasPermission(2)}, same "gamemasters" tier vanilla's own
 * cheat-y commands use - ground-truthed against {@code Commands.LEVEL_GAMEMASTERS}
 * on the resolved NeoForge jar) DEBUG/PLACEHOLDER seam so the whole
 * unlock loop (this command -&gt; {@code SkillProgressAttachment#grantPoints}
 * -&gt; re-sync -&gt; GUI shows new available points -&gt; click an AVAILABLE node
 * -&gt; {@code network.SkillUnlockRequestPayload} -&gt;
 * {@code server.ServerSkillEvents#handleUnlockRequest}) is exercisable
 * in-game right now, without the real XP-source economy #163's phase 2/3
 * scope explicitly excludes (see {@code SkillProgressAttachment#grantPoints}'s
 * doc - "exposed now so the point economy has a single, obvious seam for
 * that later phase to call into"). This command IS that seam's first
 * caller, not the real economy itself; a later phase replacing it only
 * needs to add a new caller of {@code grantPoints}, not touch this class.
 *
 * <p><b>Economy phase addition: {@code /vppskills respec}.</b> Unlike
 * {@code grantpoints}, this is a normal-player-facing command (no
 * permission gate at the {@code vppskills} root - see below), so the root
 * literal's own {@code requires} moved from a blanket
 * {@code hasPermission(2)} down onto {@code grantpoints} specifically. Plain
 * {@code respec} consumes the player's own one-time free respec token
 * ({@code SkillProgressAttachment#consumeFreeRespec()} - the #163 economy
 * cutover mechanism) if they still have it, refusing with a chat message if
 * not. {@code respec force} is the {@code hasPermission(2)} admin escape
 * hatch that bypasses the token entirely (e.g. to fix a player who's stuck,
 * or for repeated testing). Both variants share {@link #performRespec} so
 * the actual mutation (clear nodes/attributes, resync) can never drift
 * between the token-gated and forced paths.
 */
@EventBusSubscriber(modid = VppSkills.MODID)
public final class VppSkillsCommand {

    @SubscribeEvent
    static void onRegisterCommands(RegisterCommandsEvent event) {
        event.getDispatcher().register(
                Commands.literal("vppskills")
                        .then(Commands.literal("grantpoints")
                                .requires(source -> source.hasPermission(2))
                                .then(Commands.argument("amount", IntegerArgumentType.integer(1))
                                        .executes(context -> {
                                            ServerPlayer player = context.getSource().getPlayerOrException();
                                            int amount = IntegerArgumentType.getInteger(context, "amount");

                                            SkillProgressAttachment progress = player.getData(ModAttachments.SKILL_PROGRESS);
                                            progress.grantPoints(amount);
                                            ServerSkillEvents.syncToPlayer(player);

                                            context.getSource().sendSuccess(
                                                    () -> Component.literal("vppskills: granted " + amount + " skill point(s) - now " + progress.availablePoints() + " available."),
                                                    true);
                                            return com.mojang.brigadier.Command.SINGLE_SUCCESS;
                                        })))
                        .then(Commands.literal("respec")
                                .executes(context -> {
                                    ServerPlayer player = context.getSource().getPlayerOrException();
                                    SkillProgressAttachment progress = player.getData(ModAttachments.SKILL_PROGRESS);

                                    if (!progress.consumeFreeRespec()) {
                                        context.getSource().sendFailure(
                                                Component.literal("vppskills: no free respec remaining - ask an admin for /vppskills respec force."));
                                        return 0;
                                    }

                                    performRespec(player, progress, context.getSource());
                                    return com.mojang.brigadier.Command.SINGLE_SUCCESS;
                                })
                                .then(Commands.literal("force")
                                        .requires(source -> source.hasPermission(2))
                                        .executes(context -> {
                                            ServerPlayer player = context.getSource().getPlayerOrException();
                                            SkillProgressAttachment progress = player.getData(ModAttachments.SKILL_PROGRESS);

                                            performRespec(player, progress, context.getSource());
                                            return com.mojang.brigadier.Command.SINGLE_SUCCESS;
                                        }))));
    }

    /**
     * The mutation shared by plain {@code respec} (after its free-token
     * check) and {@code respec force} (which skips that check entirely):
     * capture the unlocked node ids via {@code fullRespec()} (which already
     * moved spent -&gt; available), clear their attribute modifiers, then
     * resync the client - the exact order {@code ServerSkillEvents#handleUnlockRequest}
     * follows for a single unlock, just reversed and applied to every
     * previously-unlocked node at once.
     */
    private static void performRespec(ServerPlayer player, SkillProgressAttachment progress, CommandSourceStack source) {
        Set<String> clearedNodeIds = progress.fullRespec();
        SkillAttributeApplier.clearAll(player, clearedNodeIds);
        ServerSkillEvents.syncToPlayer(player);

        source.sendSuccess(
                () -> Component.literal("vppskills: respec complete - cleared " + clearedNodeIds.size()
                        + " node(s), " + progress.availablePoints() + " skill point(s) now available."),
                true);
    }

    private VppSkillsCommand() {
    }
}
