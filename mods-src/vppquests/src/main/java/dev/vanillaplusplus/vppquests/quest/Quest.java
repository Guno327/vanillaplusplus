package dev.vanillaplusplus.vppquests.quest;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import net.minecraft.resources.ResourceLocation;

import java.util.ArrayList;
import java.util.List;

/**
 * A single quest definition, data-driven from
 * {@code data/<namespace>/vppquests/quest/<chapter>/<slug>.json}. See
 * DESIGN.md's GitHub issue #109 design-proposal section for the full JSON
 * shape this mirrors - real multi-parent {@link #dependencies()} (a true
 * DAG, not vanilla advancements' single-parent collapse), plus the new
 * {@link #criticalPath()} flag the eventual questline rebuild (Phase D,
 * deferred) needs to compute a deterministic "next quest."
 *
 * <p>{@code id} is the quest's {@code <chapter>/<slug>} resource location,
 * mirroring the existing {@code "<chapter>__<slug>"} string ids
 * {@code gen_quests.py} emits today (a future migration/generator maps one
 * to the other trivially).
 */
public record Quest(
        ResourceLocation id,
        ResourceLocation chapter,
        String title,
        List<String> description,
        ResourceLocation icon,
        Frame frame,
        List<ResourceLocation> dependencies,
        List<QuestTask> tasks,
        List<QuestReward> rewards,
        boolean criticalPath) {

    public enum Frame {
        TASK, GOAL, CHALLENGE;

        static Frame fromJson(JsonObject json) {
            if (!json.has("frame")) {
                return TASK;
            }
            return Frame.valueOf(json.get("frame").getAsString().toUpperCase(java.util.Locale.ROOT));
        }
    }

    /**
     * Parses one quest JSON file's contents. {@code id} is supplied by the
     * reload listener (derived from the resource path, same convention
     * {@link net.minecraft.server.packs.resources.SimpleJsonResourceReloadListener}
     * callers already use for recipes/advancements), not read from the JSON
     * body itself.
     */
    public static Quest fromJson(ResourceLocation id, JsonObject json) {
        ResourceLocation chapter = ResourceLocation.parse(json.get("chapter").getAsString());
        String title = json.get("title").getAsString();

        List<String> description = new ArrayList<>();
        if (json.has("description")) {
            for (JsonElement e : json.getAsJsonArray("description")) {
                description.add(e.getAsString());
            }
        }

        ResourceLocation icon = ResourceLocation.parse(json.get("icon").getAsString());
        Frame frame = Frame.fromJson(json);

        List<ResourceLocation> dependencies = new ArrayList<>();
        if (json.has("dependencies")) {
            for (JsonElement e : json.getAsJsonArray("dependencies")) {
                dependencies.add(ResourceLocation.parse(e.getAsString()));
            }
        }

        List<QuestTask> tasks = new ArrayList<>();
        JsonArray tasksJson = json.getAsJsonArray("tasks");
        if (tasksJson != null) {
            for (JsonElement e : tasksJson) {
                tasks.add(QuestTask.fromJson(e.getAsJsonObject()));
            }
        }

        List<QuestReward> rewards = new ArrayList<>();
        JsonArray rewardsJson = json.getAsJsonArray("rewards");
        if (rewardsJson != null) {
            for (JsonElement e : rewardsJson) {
                rewards.add(QuestReward.fromJson(e.getAsJsonObject()));
            }
        }

        boolean criticalPath = json.has("criticalPath") && json.get("criticalPath").getAsBoolean();

        return new Quest(id, chapter, title, description, icon, frame, dependencies, tasks, rewards, criticalPath);
    }
}
