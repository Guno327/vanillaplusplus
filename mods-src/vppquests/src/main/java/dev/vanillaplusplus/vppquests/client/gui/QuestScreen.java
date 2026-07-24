package dev.vanillaplusplus.vppquests.client.gui;

import dev.vanillaplusplus.vppquests.client.ClientQuestState;
import dev.vanillaplusplus.vppquests.quest.Quest;
import dev.vanillaplusplus.vppquests.quest.QuestChapter;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;

import java.util.List;

/**
 * Phase A's GUI: a list-per-chapter view with a detail panel, per DESIGN.md's
 * #109 design-proposal "Risks" section explicit recommendation ("Recommend
 * Phase A ship a simpler list-per-chapter-with-detail-panel view first ...
 * and treat the full pannable tree as a stretch goal ... rather than
 * blocking the whole mod on getting tree-rendering right on the first
 * attempt"). A real pannable dependency-graph canvas (nodes + dependency
 * lines, multi-parent DAG rendering) is the single biggest piece of GUI
 * work still remaining - see this mod's README.md "What Phase A does NOT
 * include yet".
 *
 * <p>Reads only from {@link ClientQuestState} - the client-side mirror kept
 * current by the server's sync payloads - never touches the network
 * directly.
 */
public final class QuestScreen extends Screen {

    /** Left edge of the title and the quest-list column. */
    private static final int CONTENT_X = 10;
    /** Title baseline, sitting just below the chapter-tab row (tabs: y=8, h=20). */
    private static final int TITLE_Y = 8 + 24;
    /**
     * Wrap width for the title and the width of the quest-list column. The
     * quest buttons are 190px wide, so wrapping the title at the same width
     * keeps it inside its column and lets us measure a multi-line title.
     */
    private static final int CONTENT_WIDTH = 190;
    /** Vertical gap between the bottom of the title block and the first row. */
    private static final int TITLE_GAP = 4;
    /** Step between successive quest rows (20px button + 2px gap). */
    private static final int ROW_HEIGHT = 22;

    private ResourceLocation selectedChapter;
    private Quest selectedQuest;

    /**
     * Y of the first content row (quest list / detail panel), derived from the
     * title's actual rendered height so it always clears the title - including
     * when a long title wraps onto multiple lines.
     */
    private int contentTop() {
        return TITLE_Y + font.wordWrapHeight(title, CONTENT_WIDTH) + TITLE_GAP;
    }

    public QuestScreen() {
        super(Component.translatable("gui.vppquests.quest_screen.title"));
    }

    @Override
    protected void init() {
        List<QuestChapter> chapters = ClientQuestState.chaptersSorted();
        if (selectedChapter == null && !chapters.isEmpty()) {
            selectedChapter = chapters.get(0).id();
        }

        int tabX = 10;
        for (QuestChapter chapter : chapters) {
            ResourceLocation chapterId = chapter.id();
            addRenderableWidget(Button.builder(Component.literal(chapter.title()), b -> {
                        selectedChapter = chapterId;
                        selectedQuest = null;
                        refreshWidgets();
                    })
                    .bounds(tabX, 8, 90, 20)
                    .build());
            tabX += 94;
        }

        if (selectedChapter != null) {
            int y = contentTop();
            for (Quest quest : ClientQuestState.questsInChapter(selectedChapter)) {
                boolean complete = ClientQuestState.isComplete(quest.id());
                String prefix = complete ? "[x] " : "[ ] ";
                addRenderableWidget(Button.builder(Component.literal(prefix + quest.title()), b -> selectedQuest = quest)
                        .bounds(CONTENT_X, y, CONTENT_WIDTH, 20)
                        .build());
                y += ROW_HEIGHT;
            }
        }
    }

    private void refreshWidgets() {
        clearWidgets();
        init();
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
        renderBackground(graphics, mouseX, mouseY, partialTick);
        super.render(graphics, mouseX, mouseY, partialTick);

        graphics.drawWordWrap(font, title, CONTENT_X, TITLE_Y, CONTENT_WIDTH, 0xFFFFFF);

        if (selectedQuest != null) {
            renderDetailPanel(graphics);
        }
    }

    private void renderDetailPanel(GuiGraphics graphics) {
        int x = 210;
        int y = contentTop();
        graphics.drawString(font, Component.literal(selectedQuest.title()), x, y, 0xFFFF55, false);
        y += 14;

        for (String line : selectedQuest.description()) {
            graphics.drawString(font, Component.literal(line), x, y, 0xCCCCCC, false);
            y += 11;
        }

        y += 6;
        List<dev.vanillaplusplus.vppquests.quest.QuestTask> tasks = selectedQuest.tasks();
        for (int i = 0; i < tasks.size(); i++) {
            dev.vanillaplusplus.vppquests.quest.QuestTask task = tasks.get(i);
            int current = ClientQuestState.taskProgress(selectedQuest.id(), i);
            graphics.drawString(font, Component.literal("- " + task.describeProgress(current)), x, y, 0xAAAAAA, false);
            y += 11;
        }
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }
}
