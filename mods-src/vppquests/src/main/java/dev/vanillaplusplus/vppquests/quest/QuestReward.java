package dev.vanillaplusplus.vppquests.quest;

import com.google.gson.JsonObject;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;

/**
 * The 5 reward types {@code quests.js} already implements (only item/xp are
 * actually exercised by today's 62 quests, per {@code gen_quests.py}'s own
 * docstring - command/gamestage/toast carried over for completeness/future
 * content, same as the existing system). See DESIGN.md's #109 design-proposal
 * section, "Data model" subsection.
 */
public sealed interface QuestReward {

    String type();

    /**
     * Human-readable, registry-resolved reward line for the quest-panel GUI
     * (GitHub #164 item 5, reward-display half) - mirrors
     * {@link QuestTask#describe(int)}'s same "resolve the id to a display
     * name, don't show raw namespace:path" convention. Every case overrides
     * this; there is no sane generic fallback across 5 unrelated shapes.
     */
    Component describe();

    record ItemReward(ResourceLocation item, int count) implements QuestReward {
        @Override
        public String type() {
            return "item";
        }

        @Override
        public Component describe() {
            Component name = BuiltInRegistries.ITEM.getOptional(item)
                    .map(resolved -> (Component) new ItemStack(resolved).getHoverName())
                    .orElseGet(() -> Component.literal(item.toString()));
            return Component.literal(count + "x ").append(name);
        }
    }

    record XpReward(String category, int amount) implements QuestReward {
        @Override
        public String type() {
            return "xp";
        }

        @Override
        public Component describe() {
            return Component.literal(amount + " " + category + " XP");
        }
    }

    record CommandReward(String command) implements QuestReward {
        @Override
        public String type() {
            return "command";
        }

        @Override
        public Component describe() {
            return Component.literal("Special reward");
        }
    }

    record GamestageReward(String stage) implements QuestReward {
        @Override
        public String type() {
            return "gamestage";
        }

        @Override
        public Component describe() {
            return Component.literal("Unlocks: " + stage);
        }
    }

    record ToastReward(String title, String description) implements QuestReward {
        @Override
        public String type() {
            return "toast";
        }

        @Override
        public Component describe() {
            return Component.literal(title);
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
