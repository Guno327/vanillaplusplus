package dev.vanillaplusplus.vppquests.client.gui;

import dev.vanillaplusplus.vppquests.client.ClientQuestState;
import dev.vanillaplusplus.vppquests.quest.Quest;
import dev.vanillaplusplus.vppquests.quest.QuestChapter;
import dev.vanillaplusplus.vppquests.quest.QuestReward;
import dev.vanillaplusplus.vppquests.quest.QuestTask;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;

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
 *
 * <p><b>GitHub #164 GUI fixes.</b> The chapter ("tier") row is drawn manually
 * as a horizontally <em>scrollable</em> strip (mouse-wheel, with on-screen
 * arrow hints) inside a scissor clip, so it no longer runs off the right edge
 * and gets un-reachable at GUI scale 4 (item&nbsp;6). The detail panel's
 * title, description and task lines are all word-wrapped to the panel width so
 * long text no longer trails off the page (item&nbsp;1), and task lines show
 * registry-resolved display names rather than raw ids (item&nbsp;4, via
 * {@link QuestTask#describe(int)}).
 *
 * <p><b>Reward display + Claim button (GitHub #164 item 5).</b> The detail
 * panel now lists each quest's rewards ({@link QuestReward#describe()}) below
 * its tasks, and - once every task is done - a Claim button. Rewards are no
 * longer auto-granted on completion; clicking Claim is what actually requests
 * the grant, via {@link ClientQuestState#requestClaim}, which the server
 * re-validates before granting anything (see
 * {@code QuestProgressTracker#claimReward}). The button is drawn/hit-tested
 * manually, the same way the chapter strip above already is, rather than as a
 * vanilla {@link Button} widget - its position depends on the word-wrapped
 * height of the currently *selected* quest's description/tasks/rewards, which
 * changes without an {@link #init()} rebuild (selecting a quest is just a
 * field write), so a fixed-position vanilla widget can't track it.
 */
public final class QuestScreen extends Screen {

    /** Left edge of the title and the quest-list column. */
    private static final int CONTENT_X = 10;

    /** The chapter ("tier") strip geometry. */
    private static final int STRIP_Y = 8;
    private static final int STRIP_H = 20;
    private static final int TAB_W = 90;
    private static final int TAB_GAP = 4;
    private static final int TAB_STEP = TAB_W + TAB_GAP;
    /** Pixels of horizontal travel per wheel notch over the strip. */
    private static final int STRIP_SCROLL_STEP = 30;

    /** Title baseline, sitting just below the chapter-tab strip. */
    private static final int TITLE_Y = STRIP_Y + STRIP_H + 6;
    /** Wrap width / column width shared by the title and the quest-list buttons. */
    private static final int CONTENT_WIDTH = 190;
    /** Vertical gap between the bottom of the title block and the first row. */
    private static final int TITLE_GAP = 4;
    /** Step between successive quest rows (20px button + 2px gap). */
    private static final int ROW_HEIGHT = 22;

    /** Left edge of the detail panel and its right-hand margin. */
    private static final int PANEL_X = 210;
    private static final int PANEL_MARGIN = 10;

    /** Claim button geometry, matching the chapter strip's own fixed-size convention. */
    private static final int CLAIM_BUTTON_W = 80;
    private static final int CLAIM_BUTTON_H = 20;

    private ResourceLocation selectedChapter;
    private Quest selectedQuest;

    /** Horizontal scroll offset of the chapter strip, clamped in render/input. */
    private int chapterScrollX;

    /**
     * Claim button hit-box for the currently rendered frame, recomputed every
     * {@link #renderDetailPanel} call (its y depends on word-wrapped text
     * heights that change per selected quest) - {@code null} when no claimable
     * button should be drawn/hit-tested this frame (no quest selected, quest
     * incomplete, or already claimed).
     */
    private ClaimButtonBounds claimButtonBounds;

    private record ClaimButtonBounds(int x, int y, int w, int h, boolean alreadyClaimed) {
        boolean contains(double mouseX, double mouseY) {
            return mouseX >= x && mouseX < x + w && mouseY >= y && mouseY < y + h;
        }
    }

    public QuestScreen() {
        super(Component.translatable("gui.vppquests.quest_screen.title"));
    }

    /**
     * Y of the first content row (quest list / detail panel), derived from the
     * title's actual rendered height so it always clears the title - including
     * when a long title wraps onto multiple lines.
     */
    private int contentTop() {
        return TITLE_Y + font.wordWrapHeight(title, CONTENT_WIDTH) + TITLE_GAP;
    }

    /** Right edge of the (full-width) chapter strip's visible/clip region. */
    private int stripRight() {
        return width - CONTENT_X;
    }

    /** Total pixel width of all chapter tabs laid end to end. */
    private int stripContentWidth() {
        int count = ClientQuestState.chaptersSorted().size();
        return count == 0 ? 0 : count * TAB_STEP - TAB_GAP;
    }

    private int maxChapterScroll() {
        return Math.max(0, stripContentWidth() - (stripRight() - CONTENT_X));
    }

    @Override
    protected void init() {
        List<QuestChapter> chapters = ClientQuestState.chaptersSorted();
        if (selectedChapter == null && !chapters.isEmpty()) {
            selectedChapter = chapters.get(0).id();
        }

        // The chapter ("tier") strip is drawn + hit-tested manually (see
        // render / mouseClicked / mouseScrolled) so it can scroll and clip;
        // only the quest-list buttons are vanilla widgets.
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

        renderChapterStrip(graphics, mouseX, mouseY);

        graphics.drawWordWrap(font, title, CONTENT_X, TITLE_Y, CONTENT_WIDTH, 0xFFFFFF);

        if (selectedQuest != null) {
            renderDetailPanel(graphics, mouseX, mouseY);
        }
    }

    private void renderChapterStrip(GuiGraphics graphics, int mouseX, int mouseY) {
        List<QuestChapter> chapters = ClientQuestState.chaptersSorted();
        if (chapters.isEmpty()) {
            return;
        }
        chapterScrollX = Mth.clamp(chapterScrollX, 0, maxChapterScroll());

        int left = CONTENT_X;
        int right = stripRight();
        graphics.enableScissor(left, STRIP_Y, right, STRIP_Y + STRIP_H);
        for (int i = 0; i < chapters.size(); i++) {
            QuestChapter chapter = chapters.get(i);
            int tabX = left + i * TAB_STEP - chapterScrollX;
            if (tabX + TAB_W <= left || tabX >= right) {
                continue; // fully clipped - skip
            }
            boolean selected = chapter.id().equals(selectedChapter);
            boolean hovered = mouseY >= STRIP_Y && mouseY < STRIP_Y + STRIP_H
                    && mouseX >= tabX && mouseX < tabX + TAB_W
                    && mouseX >= left && mouseX < right;
            int bg = selected ? 0xFF3A3A6A : (hovered ? 0xC0505050 : 0xC0202020);
            graphics.fill(tabX, STRIP_Y, tabX + TAB_W, STRIP_Y + STRIP_H, bg);
            if (selected) {
                // Bright underline so the active tier reads clearly.
                graphics.fill(tabX, STRIP_Y + STRIP_H - 2, tabX + TAB_W, STRIP_Y + STRIP_H, 0xFFFFCC33);
            }
            String label = ellipsize(chapter.title(), TAB_W - 6);
            int textColor = selected ? 0xFFFFFF : 0xCCCCCC;
            graphics.drawString(font, label,
                    tabX + (TAB_W - font.width(label)) / 2,
                    STRIP_Y + (STRIP_H - font.lineHeight) / 2 + 1,
                    textColor, false);
        }
        graphics.disableScissor();

        // Scroll affordances, drawn outside the clip so they're never cut off.
        if (chapterScrollX > 0) {
            graphics.drawString(font, "<", left - 1, STRIP_Y + (STRIP_H - font.lineHeight) / 2 + 1, 0xFFFFFF, false);
        }
        if (chapterScrollX < maxChapterScroll()) {
            graphics.drawString(font, ">", right - font.width(">") + 1, STRIP_Y + (STRIP_H - font.lineHeight) / 2 + 1, 0xFFFFFF, false);
        }
    }

    private void renderDetailPanel(GuiGraphics graphics, int mouseX, int mouseY) {
        int x = PANEL_X;
        int y = contentTop();
        int wrap = Math.max(60, width - PANEL_X - PANEL_MARGIN);

        Component titleComp = Component.literal(selectedQuest.title());
        graphics.drawWordWrap(font, titleComp, x, y, wrap, 0xFFFF55);
        y += font.wordWrapHeight(titleComp, wrap) + 4;

        for (String line : selectedQuest.description()) {
            Component lineComp = Component.literal(line);
            graphics.drawWordWrap(font, lineComp, x, y, wrap, 0xCCCCCC);
            y += font.wordWrapHeight(lineComp, wrap) + 2;
        }

        y += 6;
        List<QuestTask> tasks = selectedQuest.tasks();
        for (int i = 0; i < tasks.size(); i++) {
            QuestTask task = tasks.get(i);
            int current = ClientQuestState.taskProgress(selectedQuest.id(), i);
            Component taskComp = Component.literal("- ").append(task.describe(current));
            graphics.drawWordWrap(font, taskComp, x, y, wrap, 0xAAAAAA);
            y += font.wordWrapHeight(taskComp, wrap) + 2;
        }

        y = renderRewards(graphics, x, y, wrap, mouseX, mouseY);
    }

    /**
     * Renders the rewards list plus (if the quest is complete) the Claim
     * button, and refreshes {@link #claimButtonBounds} for this frame's
     * hit-testing. Returns the y cursor after everything drawn here, in case
     * a future panel section is added below it.
     */
    private int renderRewards(GuiGraphics graphics, int x, int y, int wrap, int mouseX, int mouseY) {
        List<QuestReward> rewards = selectedQuest.rewards();
        claimButtonBounds = null;

        if (!rewards.isEmpty()) {
            y += 6;
            Component header = Component.literal("Rewards:");
            graphics.drawWordWrap(font, header, x, y, wrap, 0xFFFFFF);
            y += font.wordWrapHeight(header, wrap) + 2;

            for (QuestReward reward : rewards) {
                Component rewardComp = Component.literal("- ").append(reward.describe());
                graphics.drawWordWrap(font, rewardComp, x, y, wrap, 0x55FF55);
                y += font.wordWrapHeight(rewardComp, wrap) + 2;
            }
        }

        boolean complete = ClientQuestState.isComplete(selectedQuest.id());
        if (!complete) {
            return y;
        }

        y += 6;
        boolean claimed = ClientQuestState.isClaimed(selectedQuest.id());
        claimButtonBounds = new ClaimButtonBounds(x, y, CLAIM_BUTTON_W, CLAIM_BUTTON_H, claimed);

        boolean hovered = !claimed && claimButtonBounds.contains(mouseX, mouseY);
        int bg = claimed ? 0xFF404040 : (hovered ? 0xFF3A8F3A : 0xFF2D6B2D);
        graphics.fill(x, y, x + CLAIM_BUTTON_W, y + CLAIM_BUTTON_H, bg);
        String label = claimed ? "Claimed" : "Claim";
        graphics.drawCenteredString(font, label, x + CLAIM_BUTTON_W / 2, y + (CLAIM_BUTTON_H - font.lineHeight) / 2 + 1,
                claimed ? 0xAAAAAA : 0xFFFFFF);

        return y + CLAIM_BUTTON_H;
    }

    /** Truncates {@code text} with a trailing ellipsis to fit {@code maxWidth} px. */
    private String ellipsize(String text, int maxWidth) {
        if (font.width(text) <= maxWidth) {
            return text;
        }
        String ellipsis = "...";
        int ellipsisWidth = font.width(ellipsis);
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (font.width(out.toString() + c) + ellipsisWidth > maxWidth) {
                break;
            }
            out.append(c);
        }
        return out + ellipsis;
    }

    @Override
    public boolean mouseClicked(double mouseX, double mouseY, int button) {
        if (button == 0 && claimButtonBounds != null && !claimButtonBounds.alreadyClaimed()
                && claimButtonBounds.contains(mouseX, mouseY)) {
            ClientQuestState.requestClaim(selectedQuest.id());
            return true;
        }
        if (button == 0 && mouseY >= STRIP_Y && mouseY < STRIP_Y + STRIP_H
                && mouseX >= CONTENT_X && mouseX < stripRight()) {
            List<QuestChapter> chapters = ClientQuestState.chaptersSorted();
            int worldX = (int) mouseX - CONTENT_X + chapterScrollX;
            int index = worldX / TAB_STEP;
            int withinTab = worldX - index * TAB_STEP;
            if (index >= 0 && index < chapters.size() && withinTab < TAB_W) {
                ResourceLocation clicked = chapters.get(index).id();
                if (!clicked.equals(selectedChapter)) {
                    selectedChapter = clicked;
                    selectedQuest = null;
                    refreshWidgets();
                }
            }
            return true; // consume clicks anywhere on the strip
        }
        return super.mouseClicked(mouseX, mouseY, button);
    }

    @Override
    public boolean mouseScrolled(double mouseX, double mouseY, double scrollX, double scrollY) {
        if (mouseY >= STRIP_Y && mouseY < STRIP_Y + STRIP_H
                && mouseX >= CONTENT_X && mouseX < stripRight() && maxChapterScroll() > 0) {
            // Wheel up (scrollY > 0) reveals earlier tiers; wheel down, later ones.
            chapterScrollX = Mth.clamp(chapterScrollX - (int) (scrollY * STRIP_SCROLL_STEP), 0, maxChapterScroll());
            return true;
        }
        return super.mouseScrolled(mouseX, mouseY, scrollX, scrollY);
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }
}
