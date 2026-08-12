package dev.vanillaplusplus.vppquests.quest;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.resources.ResourceLocation;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

/** Unit tests for {@link QuestReward#fromJson}, covering all 5 reward types and their optional-field defaults. */
class QuestRewardTest {

    private static JsonObject parse(String json) {
        return JsonParser.parseString(json).getAsJsonObject();
    }

    @Test
    void itemRewardParsesItemAndCount() {
        QuestReward reward = QuestReward.fromJson(parse("{\"type\":\"item\",\"item\":\"minecraft:diamond\",\"count\":5}"));

        assertEquals("item", reward.type());
        QuestReward.ItemReward item = (QuestReward.ItemReward) reward;
        assertEquals(ResourceLocation.parse("minecraft:diamond"), item.item());
        assertEquals(5, item.count());
    }

    @Test
    void itemRewardDefaultsCountToOne() {
        QuestReward reward = QuestReward.fromJson(parse("{\"type\":\"item\",\"item\":\"minecraft:diamond\"}"));

        assertEquals(1, ((QuestReward.ItemReward) reward).count());
    }

    @Test
    void xpRewardParsesCategoryAndAmount() {
        QuestReward reward = QuestReward.fromJson(parse("{\"type\":\"xp\",\"category\":\"adventurer\",\"amount\":25}"));

        assertEquals("xp", reward.type());
        QuestReward.XpReward xp = (QuestReward.XpReward) reward;
        assertEquals("adventurer", xp.category());
        assertEquals(25, xp.amount());
    }

    @Test
    void commandRewardParsesCommand() {
        QuestReward reward = QuestReward.fromJson(parse("{\"type\":\"command\",\"command\":\"say hi\"}"));

        assertEquals("command", reward.type());
        assertEquals("say hi", ((QuestReward.CommandReward) reward).command());
    }

    @Test
    void gamestageRewardParsesStage() {
        QuestReward reward = QuestReward.fromJson(parse("{\"type\":\"gamestage\",\"stage\":\"iron_age\"}"));

        assertEquals("gamestage", reward.type());
        assertEquals("iron_age", ((QuestReward.GamestageReward) reward).stage());
    }

    @Test
    void toastRewardParsesTitleAndDescription() {
        QuestReward reward = QuestReward.fromJson(
                parse("{\"type\":\"toast\",\"title\":\"Nice!\",\"description\":\"Well done\"}"));

        assertEquals("toast", reward.type());
        QuestReward.ToastReward toast = (QuestReward.ToastReward) reward;
        assertEquals("Nice!", toast.title());
        assertEquals("Well done", toast.description());
    }

    @Test
    void toastRewardDefaultsTitleAndDescriptionToEmptyString() {
        QuestReward reward = QuestReward.fromJson(parse("{\"type\":\"toast\"}"));

        QuestReward.ToastReward toast = (QuestReward.ToastReward) reward;
        assertEquals("", toast.title());
        assertEquals("", toast.description());
    }

    @Test
    void unknownRewardTypeThrows() {
        assertThrows(IllegalArgumentException.class,
                () -> QuestReward.fromJson(parse("{\"type\":\"not_a_type\"}")));
    }
}
