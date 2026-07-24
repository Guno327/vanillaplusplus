package dev.vanillaplusplus.vppquests.quest;

import dev.vanillaplusplus.vppquests.VppQuests;
import dev.vanillaplusplus.vppquests.data.ModAttachments;
import dev.vanillaplusplus.vppquests.data.QuestProgressAttachment;
import dev.vanillaplusplus.vppquests.network.QuestProgressSyncPayload;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.stats.Stats;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.network.PacketDistributor;

import java.util.List;
import java.util.Optional;

/**
 * Server-side tick-driven quest evaluator: for each online player, checks
 * every not-yet-completed quest whose dependencies are already satisfied,
 * updates {@link QuestProgressAttachment} task counters, and grants rewards
 * on completion.
 *
 * <p><b>Deliberate Phase A simplifications (disclosed, mirroring the same
 * "does the player currently hold/satisfy X" pragmatism
 * {@code scripts/gen_quests.py}'s own docstring already argues for over a
 * true acquisition-event hook):</b>
 * <ul>
 *   <li>{@code item} tasks check current inventory count, not "freshly
 *   crafted."</li>
 *   <li>{@code kill} tasks read vanilla's own {@link Stats#ENTITY_KILLED}
 *   statistic (lifetime kill count for that entity type) - simpler and more
 *   robust than a custom per-quest kill-event counter, and needs no new
 *   attachment state.</li>
 *   <li>{@code dimension} tasks check the player's *current* dimension, not
 *   "ever visited."</li>
 *   <li>{@code checkmark} tasks are satisfied as soon as their dependencies
 *   are (no explicit "/quest check" acknowledgement command exists in this
 *   scaffold).</li>
 *   <li>{@code gamestage} tasks/rewards are intentionally NOT wired to any
 *   specific gamestage mod - {@code vppquests} is meant to stay a
 *   standalone, Modrinth-publishable mod (this project's own README, the
 *   {@code mods-src/<modid>/} convention GitHub #67 established), so a hard
 *   dependency on this pack's specific progression-stage mod would break
 *   that. The field round-trips through the data model/JSON/network layers
 *   unchanged for a later pack-side bridge to hook, but is never satisfied
 *   by this tracker on its own.</li>
 *   <li>{@code xp} rewards grant vanilla experience points, not this pack's
 *   RPG-skill-mod categories, for the same standalone-mod reason.</li>
 * </ul>
 * A full gameplay-accurate tracker (event-based kill/craft hooks, a real
 * gamestage bridge) is explicitly out of Phase A's scope per the task
 * boundaries - this class exists so the data-attachment "progress tracking
 * capability" the task asks for is a working, if intentionally simplified,
 * demonstration rather than inert plumbing.
 */
public final class QuestProgressTracker {

    public static void evaluate(net.minecraft.server.level.ServerPlayer player) {
        QuestProgressAttachment progress = player.getData(ModAttachments.QUEST_PROGRESS);
        boolean changed = false;

        for (Quest quest : QuestRegistry.get().allQuests()) {
            if (progress.isComplete(quest.id())) {
                continue;
            }
            if (!dependenciesSatisfied(quest, progress)) {
                continue;
            }

            boolean allTasksDone = true;
            List<QuestTask> tasks = quest.tasks();
            for (int i = 0; i < tasks.size(); i++) {
                QuestTask task = tasks.get(i);
                int current = evaluateTask(player, task);
                int previous = progress.taskProgress(quest.id(), i);
                if (current != previous) {
                    progress.setTaskProgress(quest.id(), i, current);
                    changed = true;
                }
                if (current < task.targetCount()) {
                    allTasksDone = false;
                }
            }

            if (allTasksDone) {
                progress.markComplete(quest.id());
                changed = true;
                grantRewards(player, quest);
                player.sendSystemMessage(Component.translatable("vppquests.quest.completed", quest.title()));
            }
        }

        if (changed) {
            syncProgress(player, progress);
        }
    }

    private static boolean dependenciesSatisfied(Quest quest, QuestProgressAttachment progress) {
        for (ResourceLocation dep : quest.dependencies()) {
            if (!progress.isComplete(dep)) {
                return false;
            }
        }
        return true;
    }

    private static int evaluateTask(net.minecraft.server.level.ServerPlayer player, QuestTask task) {
        return switch (task) {
            case QuestTask.Item item -> {
                Optional<Item> resolved = BuiltInRegistries.ITEM.getOptional(item.item());
                if (resolved.isEmpty()) {
                    yield 0;
                }
                int held = 0;
                for (ItemStack stack : player.getInventory().items) {
                    if (stack.is(resolved.get())) {
                        held += stack.getCount();
                    }
                }
                yield Math.min(held, item.count());
            }
            case QuestTask.Kill kill -> {
                Optional<EntityType<?>> resolved = BuiltInRegistries.ENTITY_TYPE.getOptional(kill.entity());
                if (resolved.isEmpty()) {
                    yield 0;
                }
                int killed = player.getStats().getValue(Stats.ENTITY_KILLED.get(resolved.get()));
                yield Math.min(killed, kill.count());
            }
            case QuestTask.Dimension dimension -> player.level().dimension().location().equals(dimension.dimension()) ? 1 : 0;
            case QuestTask.Gamestage ignored -> 0; // see class doc - deliberately unwired in this standalone scaffold
            case QuestTask.Checkmark ignored -> 1; // satisfied as soon as its dependencies are, see class doc
        };
    }

    private static void grantRewards(net.minecraft.server.level.ServerPlayer player, Quest quest) {
        for (QuestReward reward : quest.rewards()) {
            switch (reward) {
                case QuestReward.ItemReward item -> BuiltInRegistries.ITEM.getOptional(item.item())
                        .ifPresent(resolved -> player.getInventory().placeItemBackInInventory(new ItemStack(resolved, item.count())));
                case QuestReward.XpReward xp -> player.giveExperiencePoints(xp.amount());
                case QuestReward.CommandReward command -> {
                    String resolved = command.command().replace("{p}", player.getGameProfile().getName());
                    player.getServer().getCommands().performPrefixedCommand(player.createCommandSourceStack(), resolved);
                }
                case QuestReward.GamestageReward ignored -> VppQuests.LOGGER.debug(
                        "vppquests: gamestage reward on quest {} skipped (standalone mod, no gamestage bridge - see QuestProgressTracker)",
                        quest.id());
                case QuestReward.ToastReward toast -> player.sendSystemMessage(Component.literal(toast.title() + " - " + toast.description()));
            }
        }
    }

    private static void syncProgress(net.minecraft.server.level.ServerPlayer player, QuestProgressAttachment progress) {
        PacketDistributor.sendToPlayer(player, new QuestProgressSyncPayload(progress.toJson()));
    }

    private QuestProgressTracker() {
    }
}
