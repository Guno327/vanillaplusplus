package dev.vanillaplusplus.vppskills.tree;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import dev.vanillaplusplus.vppskills.VppSkills;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.server.packs.resources.ResourceManager;

import java.io.IOException;
import java.io.Reader;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Parses the tree data ported into this mod's own jar by build.gradle's
 * {@code importSkillTreeData} task (a build-time copy of
 * {@code pack/kubejs/data/puffish_skills/puffish_skills/categories/**} into
 * this mod's {@code assets/vppskills/tree/categories/**}).
 *
 * <p>Reads via the real client {@link ResourceManager} (not raw classpath
 * access) using the same "{@code FileToIdConverter}-shaped, hand-rolled
 * Gson" technique {@code vppquests}' {@code QuestReloadListener} already
 * proved for this pack's JSON conventions - the difference here is this
 * loader targets {@code assets/} via the CLIENT resource manager rather than
 * {@code data/} via a server {@code AddReloadListenerEvent} listener,
 * because a phase-1 proof-of-concept screen needs to render real node
 * positions on a client connected to a remote dedicated server, which never
 * has local access to that server's own {@code data/} folder - only
 * {@code assets/} ships inside every mod jar and is always available
 * client-side, resource-pack-overridable included.
 *
 * <p>This is a one-shot load (see {@code ClientSkillTreeState}), not a live
 * {@code PreparableReloadListener} registered via
 * {@code RegisterClientReloadListenersEvent} - wiring that up so {@code F3+T}
 * picks up edits is a natural, low-risk phase-2 follow-up, not done here to
 * keep this phase's diff to "port the data model + prove the canvas".
 */
public final class SkillTreeLoader {

    private static final String NAMESPACE = "vppskills";
    private static final String BASE_PATH = "tree/categories";

    private SkillTreeLoader() {
    }

    public static SkillTreeData load(ResourceManager resourceManager) {
        List<String> categoryIds = readIndex(resourceManager);
        Map<String, SkillTreeCategory> categories = new LinkedHashMap<>();
        for (String categoryId : categoryIds) {
            try {
                categories.put(categoryId, parseCategory(resourceManager, categoryId));
            } catch (IOException | RuntimeException e) {
                VppSkills.LOGGER.error("vppskills: failed to load skill tree category {}", categoryId, e);
            }
        }
        VppSkills.LOGGER.info("vppskills: loaded {} skill tree categories ({} total nodes)",
                categories.size(),
                categories.values().stream().mapToInt(c -> c.nodes().size()).sum());
        return new SkillTreeData(categories);
    }

    private static List<String> readIndex(ResourceManager resourceManager) {
        ResourceLocation indexLoc = ResourceLocation.fromNamespaceAndPath(NAMESPACE, BASE_PATH + "/index.json");
        Optional<Resource> resource = resourceManager.getResource(indexLoc);
        if (resource.isEmpty()) {
            VppSkills.LOGGER.warn("vppskills: {} not found - was importSkillTreeData run before this jar was built?",
                    indexLoc);
            return List.of();
        }
        try (Reader reader = resource.get().openAsReader()) {
            JsonArray array = JsonParser.parseReader(reader).getAsJsonArray();
            List<String> ids = new ArrayList<>();
            for (JsonElement element : array) {
                ids.add(element.getAsString());
            }
            return ids;
        } catch (IOException e) {
            VppSkills.LOGGER.error("vppskills: failed to read {}", indexLoc, e);
            return List.of();
        }
    }

    private static SkillTreeCategory parseCategory(ResourceManager resourceManager, String categoryId) throws IOException {
        String prefix = BASE_PATH + "/" + categoryId + "/";

        JsonObject categoryJson = readJsonObject(resourceManager, prefix + "category.json");
        String title = categoryJson != null && categoryJson.has("title")
                ? categoryJson.get("title").getAsString()
                : categoryId;
        String categoryIcon = extractIconItem(categoryJson);

        JsonObject definitionsJson = readJsonObject(resourceManager, prefix + "definitions.json");
        Map<String, JsonObject> definitions = new LinkedHashMap<>();
        if (definitionsJson != null) {
            for (Map.Entry<String, JsonElement> entry : definitionsJson.entrySet()) {
                definitions.put(entry.getKey(), entry.getValue().getAsJsonObject());
            }
        }

        JsonObject skillsJson = readJsonObject(resourceManager, prefix + "skills.json");
        List<SkillTreeNode> nodes = new ArrayList<>();
        if (skillsJson != null) {
            for (Map.Entry<String, JsonElement> entry : skillsJson.entrySet()) {
                String nodeId = entry.getKey();
                JsonObject nodeJson = entry.getValue().getAsJsonObject();
                String definitionId = nodeJson.has("definition") ? nodeJson.get("definition").getAsString() : null;
                JsonObject definition = definitionId != null ? definitions.get(definitionId) : null;
                nodes.add(new SkillTreeNode(
                        nodeId,
                        categoryId,
                        nodeJson.has("x") ? nodeJson.get("x").getAsDouble() : 0.0,
                        nodeJson.has("y") ? nodeJson.get("y").getAsDouble() : 0.0,
                        nodeJson.has("root") && nodeJson.get("root").getAsBoolean(),
                        definitionId,
                        definition != null && definition.has("title") ? definition.get("title").getAsString() : nodeId,
                        extractIconItem(definition)));
            }
        }

        JsonObject connectionsJson = readJsonObject(resourceManager, prefix + "connections.json");
        List<SkillTreeConnection> connections = new ArrayList<>();
        if (connectionsJson != null) {
            for (Map.Entry<String, JsonElement> groupEntry : connectionsJson.entrySet()) {
                String group = groupEntry.getKey();
                JsonObject groupJson = groupEntry.getValue().getAsJsonObject();
                if (!groupJson.has("bidirectional")) {
                    continue;
                }
                for (JsonElement pairElement : groupJson.getAsJsonArray("bidirectional")) {
                    JsonArray pair = pairElement.getAsJsonArray();
                    connections.add(new SkillTreeConnection(
                            pair.get(0).getAsString(),
                            pair.get(1).getAsString(),
                            group));
                }
            }
        }

        return new SkillTreeCategory(categoryId, title, categoryIcon, nodes, connections);
    }

    /** {@code {"icon": {"type": "item", "data": {"item": "nether_star"}}}} -> {@code "nether_star"}, else null. */
    private static String extractIconItem(JsonObject owner) {
        if (owner == null || !owner.has("icon")) {
            return null;
        }
        JsonObject icon = owner.getAsJsonObject("icon");
        if (icon == null || !icon.has("data")) {
            return null;
        }
        JsonObject data = icon.getAsJsonObject("data");
        if (data == null || !data.has("item")) {
            return null;
        }
        return data.get("item").getAsString();
    }

    private static JsonObject readJsonObject(ResourceManager resourceManager, String path) throws IOException {
        ResourceLocation location = ResourceLocation.fromNamespaceAndPath(NAMESPACE, path);
        Optional<Resource> resource = resourceManager.getResource(location);
        if (resource.isEmpty()) {
            return null;
        }
        try (Reader reader = resource.get().openAsReader()) {
            return JsonParser.parseReader(reader).getAsJsonObject();
        }
    }
}
