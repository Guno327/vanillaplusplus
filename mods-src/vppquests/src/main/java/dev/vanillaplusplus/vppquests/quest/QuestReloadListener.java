package dev.vanillaplusplus.vppquests.quest;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import dev.vanillaplusplus.vppquests.VppQuests;
import net.minecraft.resources.FileToIdConverter;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.server.packs.resources.SimplePreparableReloadListener;
import net.minecraft.util.profiling.ProfilerFiller;

import java.io.IOException;
import java.io.Reader;
import java.util.HashMap;
import java.util.Map;

/**
 * Server-side datapack reload listener: parses every quest/chapter JSON file
 * under {@code data/<namespace>/vppquests/quest/**} and
 * {@code data/<namespace>/vppquests/chapter/*.json} into
 * {@link QuestRegistry}, on both initial datapack load and {@code /reload}
 * - same "generate, don't hand-type, reload like everything else" discipline
 * DESIGN.md's #109 design-proposal section calls for ("a datapack
 * JsonReloadListener ... parses all quest JSON into an in-memory registry at
 * reload").
 *
 * <p>Uses {@link FileToIdConverter} + hand-rolled Gson parsing rather than
 * {@code SimpleJsonResourceReloadListener}'s codec-based helper, so this
 * Phase A scaffold isn't coupled to guessing that class's exact generic
 * signature across NeoForge/Minecraft versions - {@link Quest#fromJson} and
 * {@link QuestChapter#fromJson} do their own field-by-field parsing, mirroring
 * how {@code quests.js}'s generator already lays the JSON out.
 */
public final class QuestReloadListener extends SimplePreparableReloadListener<QuestReloadListener.Loaded> {

    private static final FileToIdConverter QUEST_FILES =
            FileToIdConverter.json("vppquests/quest");
    private static final FileToIdConverter CHAPTER_FILES =
            FileToIdConverter.json("vppquests/chapter");

    /**
     * Carries both the parsed records (server-side gameplay logic reads
     * these) and the original raw JSON per id (kept so
     * {@code QuestNetworkSync} can forward the exact on-disk shape to
     * clients and re-parse it there with the same {@link Quest#fromJson}/
     * {@link QuestChapter#fromJson} code, rather than needing a
     * hand-written reverse {@code toJson} for every record/task/reward
     * type just to serialize for the wire).
     */
    public record Loaded(
            Map<ResourceLocation, Quest> quests,
            Map<ResourceLocation, QuestChapter> chapters,
            Map<ResourceLocation, JsonObject> rawQuests,
            Map<ResourceLocation, JsonObject> rawChapters) {
    }

    @Override
    protected Loaded prepare(ResourceManager resourceManager, ProfilerFiller profiler) {
        Map<ResourceLocation, QuestChapter> chapters = new HashMap<>();
        Map<ResourceLocation, JsonObject> rawChapters = new HashMap<>();
        for (Map.Entry<ResourceLocation, Resource> entry : CHAPTER_FILES.listMatchingResources(resourceManager).entrySet()) {
            ResourceLocation fileId = entry.getKey();
            ResourceLocation chapterId = CHAPTER_FILES.fileToId(fileId);
            try (Reader reader = entry.getValue().openAsReader()) {
                JsonObject json = JsonParser.parseReader(reader).getAsJsonObject();
                chapters.put(chapterId, QuestChapter.fromJson(chapterId, json));
                rawChapters.put(chapterId, json);
            } catch (IOException | RuntimeException e) {
                VppQuests.LOGGER.error("vppquests: failed to parse quest chapter {}", fileId, e);
            }
        }

        Map<ResourceLocation, Quest> quests = new HashMap<>();
        Map<ResourceLocation, JsonObject> rawQuests = new HashMap<>();
        for (Map.Entry<ResourceLocation, Resource> entry : QUEST_FILES.listMatchingResources(resourceManager).entrySet()) {
            ResourceLocation fileId = entry.getKey();
            ResourceLocation questId = QUEST_FILES.fileToId(fileId);
            try (Reader reader = entry.getValue().openAsReader()) {
                JsonObject json = JsonParser.parseReader(reader).getAsJsonObject();
                quests.put(questId, Quest.fromJson(questId, json));
                rawQuests.put(questId, json);
            } catch (IOException | RuntimeException e) {
                VppQuests.LOGGER.error("vppquests: failed to parse quest {}", fileId, e);
            }
        }

        return new Loaded(quests, chapters, rawQuests, rawChapters);
    }

    @Override
    protected void apply(Loaded loaded, ResourceManager resourceManager, ProfilerFiller profiler) {
        QuestRegistry.reload(loaded.quests(), loaded.chapters(), loaded.rawQuests(), loaded.rawChapters());
        VppQuests.LOGGER.info(
                "vppquests: loaded {} chapters, {} quests",
                loaded.chapters().size(),
                loaded.quests().size());
    }
}
