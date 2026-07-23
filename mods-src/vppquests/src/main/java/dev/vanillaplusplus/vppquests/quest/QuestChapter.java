package dev.vanillaplusplus.vppquests.quest;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import net.minecraft.resources.ResourceLocation;

import java.util.ArrayList;
import java.util.List;

/**
 * A quest chapter - 1:1 with a {@code ProgressiveStages} tier, per
 * DESIGN.md's #109 design-proposal section ("Questline rebuild: structure
 * and methodology"). Phase A only ports today's 10 chapters verbatim; the
 * critical-path spine invariant described there is for the Phase D
 * questline rebuild (deferred), not enforced by this scaffold.
 */
public record QuestChapter(ResourceLocation id, String title, List<String> subtitle, ResourceLocation icon, int order) {

    public static QuestChapter fromJson(ResourceLocation id, JsonObject json) {
        String title = json.get("title").getAsString();

        List<String> subtitle = new ArrayList<>();
        if (json.has("subtitle")) {
            for (JsonElement e : json.getAsJsonArray("subtitle")) {
                subtitle.add(e.getAsString());
            }
        }

        ResourceLocation icon = ResourceLocation.parse(json.get("icon").getAsString());
        int order = json.has("order") ? json.get("order").getAsInt() : 0;

        return new QuestChapter(id, title, subtitle, icon, order);
    }
}
