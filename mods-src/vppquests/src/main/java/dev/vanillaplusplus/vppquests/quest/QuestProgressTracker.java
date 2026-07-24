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
 *   <li>{@code gamestage} tasks resolve through the optional, pack-supplied
 *   {@link GamestageBridge} rather than a hard dependency on any specific
 *   stage mod - keeping {@code vppquests} standalone/Modrinth-publishable
 *   (this project's own README, the {@code mods-src/<modid>/} convention
 *   GitHub #67 established). With no resolver wired the task stays
 *   unsatisfiable (the historical default); the Vanilla++ pack wires it to
 *   KubeJS {@code player.stages} so the chapter-"enter" quests complete on
 *   reaching each age (GitHub #166). {@code gamestage} <em>rewards</em> are
 *   still a no-op here for the same standalone reason.</li>
 *   <li>{@code xp} rewards route through the optional, pack-supplied
 *   {@link QuestRewardBridge}: unwired standalone they grant vanilla
 *   experience (the historical default), but the reward's {@code category}
 *   is a skill category, so the Vanilla++ pack wires the bridge to grant
 *   Pufferfish's Skills XP in that category (GitHub #164 item 5).</li>
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
                int previous = progress.taskProgress(quest.id(), i);
                int current = evaluateTask(player, task);
                // "onlyFromCrafting" item tasks are a monotonic latch: the
                // once-per-second inventory poll can only ever *raise* their
                // progress, never lower it. This is the core GitHub #164 item 2
                // fix - a crafted-then-immediately-consumed item (Andesite
                // Alloy -> casing, a Silent Gear pickaxe reforged, etc.) is
                // gone from the inventory before the next poll, so a pure
                // "count what you currently hold" check would silently miss it.
                // The craft counts are accumulated event-side in
                // onItemCrafted(...); here we just make sure the poll never
                // erases them. (The quest text is "Craft or pick up ...", so a
                // still-held item is still honoured via the max.)
                if (task instanceof QuestTask.Item item && item.onlyFromCrafting()) {
                    current = Math.max(previous, current);
                }
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

    /**
     * Event-side counterpart to the tick poll (GitHub #164 item 2): called
     * from {@link ServerQuestEvents} on every {@code ItemCraftedEvent}, it
     * credits {@code onlyFromCrafting} item tasks the instant the item is
     * crafted - before the player can consume it - then re-runs the normal
     * {@link #evaluate} pass so a quest whose last task this satisfied
     * completes immediately rather than waiting for some unrelated later
     * trigger. Accumulated per-task counts live in the same
     * {@link QuestProgressAttachment#taskProgress} map the poll reads, and the
     * poll's monotonic-latch rule keeps them from being clobbered.
     */
    public static void onItemCrafted(net.minecraft.server.level.ServerPlayer player, ItemStack crafted) {
        if (crafted.isEmpty()) {
            return;
        }
        QuestProgressAttachment progress = player.getData(ModAttachments.QUEST_PROGRESS);
        boolean credited = false;

        for (Quest quest : QuestRegistry.get().allQuests()) {
            if (progress.isComplete(quest.id())) {
                continue;
            }
            // Note: intentionally NOT gated on dependenciesSatisfied here. A
            // player who crafts the target item *before* clearing the quest's
            // prerequisites should still get the craft credited (it's stored
            // in the latch); the quest then completes the moment its
            // prerequisites are met, rather than silently losing that craft
            // and forcing a re-craft. evaluate(...) still enforces the
            // dependency gate before it ever marks the quest complete.
            List<QuestTask> tasks = quest.tasks();
            for (int i = 0; i < tasks.size(); i++) {
                if (tasks.get(i) instanceof QuestTask.Item item
                        && item.onlyFromCrafting()
                        && craftMatches(item, crafted)) {
                    int previous = progress.taskProgress(quest.id(), i);
                    int next = Math.min(item.count(), previous + crafted.getCount());
                    if (next != previous) {
                        progress.setTaskProgress(quest.id(), i, next);
                        credited = true;
                    }
                }
            }
        }

        if (credited) {
            // Re-run the full evaluator so completion/reward/sync happen now,
            // in one place, instead of duplicating that logic here. evaluate()
            // only syncs quests it actually touched, so also push progress
            // explicitly - a craft credited to a still-locked quest changes
            // the attachment but is skipped by evaluate's dependency gate.
            evaluate(player);
            syncProgress(player, progress);
        }
    }

    private static boolean craftMatches(QuestTask.Item task, ItemStack crafted) {
        if (task.tag()) {
            return crafted.is(net.minecraft.tags.TagKey.create(
                    net.minecraft.core.registries.Registries.ITEM, task.item()));
        }
        return BuiltInRegistries.ITEM.getOptional(task.item())
                .map(crafted::is)
                .orElse(false);
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
            // Resolved through the pack-supplied GamestageBridge (GitHub #166):
            // unwired standalone -> 0 (default), but the Vanilla++ pack points
            // it at KubeJS player.stages so the 9 chapter-"enter" quests
            // complete once their age's stage is reached.
            case QuestTask.Gamestage gamestage -> GamestageBridge.hasStage(player, gamestage.stage()) ? 1 : 0;
            case QuestTask.Checkmark ignored -> 1; // satisfied as soon as its dependencies are, see class doc
        };
    }

    private static void grantRewards(net.minecraft.server.level.ServerPlayer player, Quest quest) {
        for (QuestReward reward : quest.rewards()) {
            switch (reward) {
                case QuestReward.ItemReward item -> BuiltInRegistries.ITEM.getOptional(item.item())
                        .ifPresent(resolved -> player.getInventory().placeItemBackInInventory(new ItemStack(resolved, item.count())));
                // Routed through the pack-supplied QuestRewardBridge (GitHub
                // #164 item 5): the reward's `category` ("adventurer") is a
                // skill category, not vanilla XP. Unwired standalone -> vanilla
                // XP (default); the Vanilla++ pack grants puffish skill XP.
                case QuestReward.XpReward xp -> QuestRewardBridge.grantSkillXp(player, xp.category(), xp.amount());
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
