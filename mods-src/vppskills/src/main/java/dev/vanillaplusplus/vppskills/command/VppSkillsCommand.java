package dev.vanillaplusplus.vppskills.command;

import com.mojang.brigadier.arguments.IntegerArgumentType;
import dev.vanillaplusplus.vppskills.VppSkills;
import dev.vanillaplusplus.vppskills.data.ModAttachments;
import dev.vanillaplusplus.vppskills.data.SkillProgressAttachment;
import dev.vanillaplusplus.vppskills.server.ServerSkillEvents;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

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
 */
@EventBusSubscriber(modid = VppSkills.MODID)
public final class VppSkillsCommand {

    @SubscribeEvent
    static void onRegisterCommands(RegisterCommandsEvent event) {
        event.getDispatcher().register(
                Commands.literal("vppskills")
                        .requires(source -> source.hasPermission(2))
                        .then(Commands.literal("grantpoints")
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
                                        }))));
    }

    private VppSkillsCommand() {
    }
}
