package dev.vanillaplusplus.vppskills.tree;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import dev.vanillaplusplus.vppskills.VppSkills;
import dev.vanillaplusplus.vppskills.reward.AttributeRewardData;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.server.packs.resources.ResourceManager;

import java.io.IOException;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
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
 *
 * <p><b>Phase 3 addition - {@link #loadFromClasspath}.</b> {@link #load}
 * only ever worked client-side ({@link ResourceManager} - specifically the
 * CLIENT one, since this data lives under {@code assets/}, not {@code data/}
 * - see class doc above). #163 phase 3's server-side unlock handler
 * (see {@code server.ServerSkillTreeState}) needs the exact same tree data
 * to validate a click-to-unlock request, but a dedicated server has no
 * {@link ResourceManager} that loads {@code assets/} paths at all (those are
 * a client resource-pack concept). Since the data is baked directly into
 * THIS mod's own jar (by {@code build.gradle}'s {@code importSkillTreeData}
 * task, into {@code sourceSets.main.resources}), a plain
 * {@link ClassLoader#getResourceAsStream} read works identically under a
 * client OR a dedicated server JVM - it's just a classpath resource lookup,
 * not routed through any resource-pack/reload-listener machinery - so
 * {@link #loadFromClasspath} is the server-safe sibling of {@link #load}.
 * Both delegate to the same {@link #loadWith} parsing logic via the
 * {@link ResourceOpener} seam, so the two entry points can never drift in
 * how they interpret the JSON.
 */
public final class SkillTreeLoader {

    private static final String NAMESPACE = "vppskills";
    private static final String BASE_PATH = "tree/categories";

    private SkillTreeLoader() {
    }

    public static SkillTreeData load(ResourceManager resourceManager) {
        return loadWith(path -> {
            ResourceLocation location = ResourceLocation.fromNamespaceAndPath(NAMESPACE, path);
            Optional<Resource> resource = resourceManager.getResource(location);
            if (resource.isEmpty()) {
                return Optional.empty();
            }
            return Optional.of(resource.get().openAsReader());
        });
    }

    /** See class doc "Phase 3 addition" - the server-side (no {@link ResourceManager}) equivalent of {@link #load}. */
    public static SkillTreeData loadFromClasspath(ClassLoader classLoader) {
        return loadWith(path -> {
            String classpathPath = "assets/" + NAMESPACE + "/" + path;
            var stream = classLoader.getResourceAsStream(classpathPath);
            if (stream == null) {
                return Optional.empty();
            }
            return Optional.of(new InputStreamReader(stream, StandardCharsets.UTF_8));
        });
    }

    private static SkillTreeData loadWith(ResourceOpener opener) {
        List<String> categoryIds = readIndex(opener);
        Map<String, SkillTreeCategory> categories = new LinkedHashMap<>();
        for (String categoryId : categoryIds) {
            try {
                categories.put(categoryId, parseCategory(opener, categoryId));
            } catch (IOException | RuntimeException e) {
                VppSkills.LOGGER.error("vppskills: failed to load skill tree category {}", categoryId, e);
            }
        }
        VppSkills.LOGGER.info("vppskills: loaded {} skill tree categories ({} total nodes)",
                categories.size(),
                categories.values().stream().mapToInt(c -> c.nodes().size()).sum());
        return new SkillTreeData(categories);
    }

    private static List<String> readIndex(ResourceOpener opener) {
        String path = BASE_PATH + "/index.json";
        try {
            Optional<Reader> reader = opener.open(path);
            if (reader.isEmpty()) {
                VppSkills.LOGGER.warn("vppskills: {} not found - was importSkillTreeData run before this jar was built?", path);
                return List.of();
            }
            try (Reader r = reader.get()) {
                JsonArray array = JsonParser.parseReader(r).getAsJsonArray();
                List<String> ids = new ArrayList<>();
                for (JsonElement element : array) {
                    ids.add(element.getAsString());
                }
                return ids;
            }
        } catch (IOException e) {
            VppSkills.LOGGER.error("vppskills: failed to read {}", path, e);
            return List.of();
        }
    }

    private static SkillTreeCategory parseCategory(ResourceOpener opener, String categoryId) throws IOException {
        String prefix = BASE_PATH + "/" + categoryId + "/";

        JsonObject categoryJson = readJsonObject(opener, prefix + "category.json");
        String title = categoryJson != null && categoryJson.has("title")
                ? categoryJson.get("title").getAsString()
                : categoryId;
        String categoryIcon = extractIconItem(categoryJson);

        JsonObject definitionsJson = readJsonObject(opener, prefix + "definitions.json");
        Map<String, JsonObject> definitions = new LinkedHashMap<>();
        if (definitionsJson != null) {
            for (Map.Entry<String, JsonElement> entry : definitionsJson.entrySet()) {
                definitions.put(entry.getKey(), entry.getValue().getAsJsonObject());
            }
        }

        JsonObject skillsJson = readJsonObject(opener, prefix + "skills.json");
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
                        extractIconItem(definition),
                        extractRewards(definition)));
            }
        }

        JsonObject connectionsJson = readJsonObject(opener, prefix + "connections.json");
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

    /**
     * Extracts a node definition's {@code puffish_skills:attribute} rewards
     * (see {@link SkillTreeNode}'s "Phase 3 addition" doc) - any other
     * reward {@code type} in this pack's data is skipped rather than
     * guessed at, since #163 phase 2 only ported the attribute-reward
     * vocabulary ({@code reward.AttributeOperationTranslator}).
     */
    private static List<AttributeRewardData> extractRewards(JsonObject definition) {
        if (definition == null || !definition.has("rewards")) {
            return List.of();
        }
        List<AttributeRewardData> rewards = new ArrayList<>();
        for (JsonElement rewardElement : definition.getAsJsonArray("rewards")) {
            JsonObject rewardJson = rewardElement.getAsJsonObject();
            String type = rewardJson.has("type") ? rewardJson.get("type").getAsString() : null;
            if (!"puffish_skills:attribute".equals(type)) {
                continue;
            }
            JsonObject data = rewardJson.has("data") ? rewardJson.getAsJsonObject("data") : null;
            if (data == null || !data.has("attribute") || !data.has("value") || !data.has("operation")) {
                continue;
            }
            rewards.add(new AttributeRewardData(
                    data.get("attribute").getAsString(),
                    data.get("value").getAsDouble(),
                    data.get("operation").getAsString()));
        }
        return rewards;
    }

    private static JsonObject readJsonObject(ResourceOpener opener, String path) throws IOException {
        Optional<Reader> reader = opener.open(path);
        if (reader.isEmpty()) {
            return null;
        }
        try (Reader r = reader.get()) {
            return JsonParser.parseReader(r).getAsJsonObject();
        }
    }

    /**
     * Seam between the actual JSON-parsing logic above (shared, tested-once)
     * and where the bytes come from - a client {@link ResourceManager}
     * ({@link #load}) or a plain classpath read ({@link #loadFromClasspath})
     * - see this class's "Phase 3 addition" doc for why both exist.
     */
    @FunctionalInterface
    private interface ResourceOpener {
        Optional<Reader> open(String path) throws IOException;
    }
}
