package dev.vanillaplusplus.vppquests.quest;

import com.google.gson.JsonObject;
import net.minecraft.resources.ResourceLocation;

/**
 * The 5 reward types {@code quests.js} already implements (only item/xp are
 * actually exercised by today's 62 quests, per {@code gen_quests.py}'s own
 * docstring - command/gamestage/toast carried over for completeness/future
 * content, same as the existing system). See DESIGN.md's #109 design-proposal
 * section, "Data model" subsection.
 */
public sealed interface QuestReward {

    String type();

    record ItemReward(ResourceLocation item, int count) implements QuestReward {
        @Override
        public String type() {
            return "item";
        }
    }

    record XpReward(String category, int amount) implements QuestReward {
        @Override
        public String type() {
            return "xp";
        }
    }

    record CommandReward(String command) implements QuestReward {
        @Override
        public String type() {
            return "command";
        }
    }

    record GamestageReward(String stage) implements QuestReward {
        @Override
        public String type() {
            return "gamestage";
        }
    }

    record ToastReward(String title, String description) implements QuestReward {
        @Override
        public String type() {
            return "toast";
        }
    }

    static QuestReward fromJson(JsonObject json) {
        String type = json.get("type").getAsString();
        return switch (type) {
            case "item" -> new ItemReward(
                    ResourceLocation.parse(json.get("item").getAsString()),
                    json.has("count") ? json.get("count").getAsInt() : 1);
            case "xp" -> new XpReward(json.get("category").getAsString(), json.get("amount").getAsInt());
            case "command" -> new CommandReward(json.get("command").getAsString());
            case "gamestage" -> new GamestageReward(json.get("stage").getAsString());
            case "toast" -> new ToastReward(
                    json.has("title") ? json.get("title").getAsString() : "",
                    json.has("description") ? json.get("description").getAsString() : "");
            default -> throw new IllegalArgumentException("Unknown quest reward type: " + type);
        };
    }
}
