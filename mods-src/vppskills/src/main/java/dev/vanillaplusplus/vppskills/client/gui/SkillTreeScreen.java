package dev.vanillaplusplus.vppskills.client.gui;

import com.mojang.blaze3d.vertex.PoseStack;
import dev.vanillaplusplus.vppskills.client.ClientSkillTreeState;
import dev.vanillaplusplus.vppskills.data.SkillProgressAttachment;
import dev.vanillaplusplus.vppskills.network.SkillUnlockRequestPayload;
import dev.vanillaplusplus.vppskills.reward.AttributeRewardData;
import dev.vanillaplusplus.vppskills.tree.SkillTreeCategory;
import dev.vanillaplusplus.vppskills.tree.SkillTreeConnection;
import dev.vanillaplusplus.vppskills.tree.SkillTreeData;
import dev.vanillaplusplus.vppskills.tree.SkillTreeNode;
import dev.vanillaplusplus.vppskills.unlock.SkillUnlockValidator;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.neoforged.neoforge.network.PacketDistributor;
import org.joml.Quaternionf;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * #163's real skill-tree GUI: a pannable + zoomable node-graph canvas
 * rendering the REAL node positions/connectors ported from puffish_skills'
 * generated tree data (see {@code tree.SkillTreeLoader}), now (phase 3)
 * actually interactive - every node is drawn in one of three states via
 * {@link NodeVisualState} (allocated/available/locked, mirrored from
 * {@code client.ClientSkillTreeState#progress()}), hovering shows a tooltip
 * with the node's title + reward summary, clicking an AVAILABLE node sends a
 * {@link SkillUnlockRequestPayload} to the server (which alone decides
 * whether it actually succeeds - see {@code server.ServerSkillEvents}), and
 * an available/spent points HUD readout is drawn in a corner. Opened via
 * {@code ModKeyMappings.OPEN_SKILL_TREE_SCREEN} (default {@code P}).
 *
 * <p><b>Rendering approach</b> (see {@link #render}): everything in
 * tree-space (nodes' raw {@code x}/{@code y} from puffish_skills' JSON, no
 * per-node manual transform) is drawn inside one
 * {@link PoseStack#pushPose()}/{@link PoseStack#translate}/
 * {@link PoseStack#scale} block, so pan is a translate and zoom is a scale -
 * {@link GuiGraphics}'s draw calls (confirmed via {@code javap} against the
 * resolved NeoForge/Minecraft jars: {@code fill}, {@code hLine}/
 * {@code vLine}, {@code drawString} all read {@link GuiGraphics#pose()}) all
 * respect that transform automatically. {@link GuiGraphics} has no
 * arbitrary-angle line primitive (only axis-aligned {@code hLine}/
 * {@code vLine} - ground-truthed, see class doc history), so curved
 * connectors are approximated the same way vanilla GUIs fake non-axis-aligned
 * shapes without a custom shader: {@link #drawThickSegment} pushes a nested
 * pose, translates to a segment's midpoint, rotates around Z with
 * {@link Quaternionf#rotationZ(float)}, and fills a thin rectangle - a
 * quadratic Bezier ({@link #drawCurve}) is sampled into
 * {@value #CURVE_SEGMENTS} such segments per edge for a PoE-style arc.
 */
public final class SkillTreeScreen extends Screen {

    private static final int CURVE_SEGMENTS = 14;
    private static final float NODE_HALF_SIZE = 6.0f;
    private static final float ROOT_NODE_HALF_SIZE = 9.0f;
    // Must be >= 2: GuiGraphics#fill takes int bounds, and half of this value
    // is truncated to an int below - anything under 2 would truncate to a
    // zero-height (invisible) rectangle.
    private static final float LINE_THICKNESS = 2.0f;
    private static final float MIN_ZOOM = 0.15f;
    private static final float MAX_ZOOM = 6.0f;

    private static final int COLOR_NORMAL_EDGE = 0xFF6B6B6B;
    private static final int COLOR_EXCLUSIVE_EDGE = 0xFFB25050;
    // Fill colors are keyed off NodeVisualState (allocated/available/locked)
    // rather than root-vs-normal, per #163 phase 3's brief - see NodeVisualState.
    private static final int COLOR_NODE_ALLOCATED = 0xFF3FA34D;
    private static final int COLOR_NODE_AVAILABLE = 0xFF3A6EA5;
    private static final int COLOR_NODE_LOCKED = 0xFF4A4A4A;
    private static final int COLOR_NODE_BORDER = 0xFF10141A;
    private static final int COLOR_NODE_HOVER = 0xFFFFFFFF;

    /** Screen-space anchor the tree's own (0,0) origin renders at before pan/zoom. */
    private float originScreenX;
    private float originScreenY;

    /** User pan offset, screen pixels, applied after the origin anchor. */
    private float panX;
    private float panY;

    private float zoom = 1.0f;

    /**
     * category id -> (node id -> node), built once in {@link #init()} rather
     * than per frame - with ~800 nodes/connections in the pack's real data,
     * rebuilding this map on every {@link #render} call would be wasted work
     * 60+ times a second for data that never changes while the screen is open.
     */
    private Map<String, Map<String, SkillTreeNode>> nodeIndexByCategory = Map.of();

    public SkillTreeScreen() {
        super(Component.translatable("gui.vppskills.skill_tree_screen.title"));
    }

    @Override
    protected void init() {
        originScreenX = this.width / 2.0f;
        originScreenY = this.height / 2.0f;

        Map<String, Map<String, SkillTreeNode>> index = new HashMap<>();
        for (SkillTreeCategory category : ClientSkillTreeState.get().categoriesSorted()) {
            Map<String, SkillTreeNode> byId = new HashMap<>();
            for (SkillTreeNode node : category.nodes()) {
                byId.put(node.id(), node);
            }
            index.put(category.id(), byId);
        }
        nodeIndexByCategory = index;
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
        renderBackground(graphics, mouseX, mouseY, partialTick);

        SkillTreeData data = ClientSkillTreeState.get();
        List<SkillTreeCategory> categories = data.categoriesSorted();
        if (categories.isEmpty()) {
            graphics.drawCenteredString(font,
                    "No skill tree data loaded (see vppskills log for details)",
                    this.width / 2, this.height / 2, 0xFFAAAA);
            super.render(graphics, mouseX, mouseY, partialTick);
            return;
        }

        SkillProgressAttachment progress = ClientSkillTreeState.progress();
        HoveredNode hoveredNode = findHovered(mouseX, mouseY);

        int canvasTop = 24;
        int canvasBottom = this.height - 6;
        graphics.enableScissor(0, canvasTop, this.width, canvasBottom);

        graphics.pose().pushPose();
        graphics.pose().translate(originScreenX + panX, originScreenY + panY, 0);
        graphics.pose().scale(zoom, zoom, 1.0f);

        for (SkillTreeCategory category : categories) {
            Map<String, SkillTreeNode> byId = nodeIndexByCategory.getOrDefault(category.id(), Map.of());

            for (SkillTreeConnection connection : category.connections()) {
                SkillTreeNode from = byId.get(connection.fromId());
                SkillTreeNode to = byId.get(connection.toId());
                if (from == null || to == null) {
                    continue;
                }
                int color = "exclusive".equals(connection.group()) ? COLOR_EXCLUSIVE_EDGE : COLOR_NORMAL_EDGE;
                drawCurve(graphics, from.x(), from.y(), to.x(), to.y(), color);
            }

            for (SkillTreeNode node : category.nodes()) {
                boolean isHovered = hoveredNode != null && hoveredNode.node() == node;
                NodeVisualState state = NodeVisualState.of(node, category, progress);
                drawNode(graphics, node, state, isHovered);
            }
        }

        graphics.pose().popPose();
        graphics.disableScissor();

        graphics.drawCenteredString(font, title, this.width / 2, 8, 0xFFFFFF);
        graphics.drawString(font,
                "drag to pan, scroll to zoom, click an available node to unlock it",
                6, this.height - 14, 0x999999, false);
        graphics.drawString(font,
                String.format(Locale.ROOT, "Points: %d available / %d spent",
                        progress.availablePoints(), progress.spentPoints()),
                6, this.height - 26, 0xFFFFFF, false);

        if (hoveredNode != null) {
            graphics.renderComponentTooltip(font, buildTooltip(hoveredNode, progress), mouseX, mouseY);
        }

        super.render(graphics, mouseX, mouseY, partialTick);
    }

    /** Title + reward summary (if any) + current unlock state, per #163 phase 3's hover-tooltip requirement. */
    private List<Component> buildTooltip(HoveredNode hoveredNode, SkillProgressAttachment progress) {
        SkillTreeNode node = hoveredNode.node();
        List<Component> lines = new ArrayList<>();
        lines.add(Component.literal(node.title()));
        for (AttributeRewardData reward : node.rewards()) {
            lines.add(formatReward(reward).withStyle(ChatFormatting.GRAY));
        }
        NodeVisualState state = NodeVisualState.of(node, hoveredNode.category(), progress);
        lines.add(switch (state) {
            case ALLOCATED -> Component.literal("Unlocked").withStyle(ChatFormatting.GREEN);
            case AVAILABLE -> Component.literal("Click to unlock (" + SkillUnlockValidator.NODE_COST + " point)").withStyle(ChatFormatting.YELLOW);
            case LOCKED -> Component.literal("Locked").withStyle(ChatFormatting.RED);
        });
        return lines;
    }

    /** {@code {"attribute": "generic.max_health", "value": 0.006, "operation": "multiply_total"}} -> {@code "max health +0.6%"}. */
    private static MutableComponent formatReward(AttributeRewardData reward) {
        String magnitude = switch (reward.operation()) {
            case "multiply_base", "multiply_total" -> String.format(Locale.ROOT, "%+.1f%%", reward.value() * 100.0);
            default -> String.format(Locale.ROOT, "%+.2f", reward.value());
        };
        return Component.literal(shortAttributeName(reward.attributeId()) + " " + magnitude);
    }

    private static String shortAttributeName(String attributeId) {
        String path = attributeId.contains(":") ? attributeId.substring(attributeId.indexOf(':') + 1) : attributeId;
        int dot = path.lastIndexOf('.');
        String name = dot >= 0 ? path.substring(dot + 1) : path;
        return name.replace('_', ' ');
    }

    private void drawNode(GuiGraphics graphics, SkillTreeNode node, NodeVisualState state, boolean hovered) {
        float half = node.root() ? ROOT_NODE_HALF_SIZE : NODE_HALF_SIZE;
        float x = (float) node.x();
        float y = (float) node.y();
        int fillColor = switch (state) {
            case ALLOCATED -> COLOR_NODE_ALLOCATED;
            case AVAILABLE -> COLOR_NODE_AVAILABLE;
            case LOCKED -> COLOR_NODE_LOCKED;
        };
        graphics.fill((int) (x - half), (int) (y - half), (int) (x + half), (int) (y + half), COLOR_NODE_BORDER);
        float inner = half - 1.5f;
        graphics.fill((int) (x - inner), (int) (y - inner), (int) (x + inner), (int) (y + inner), fillColor);
        if (hovered) {
            graphics.fill((int) (x - inner), (int) (y - inner), (int) (x + inner), (int) (y - inner + 1), COLOR_NODE_HOVER);
        }
    }

    /** One node under the cursor in tree-space, plus the category that owns it (needed for {@link NodeVisualState#of}). */
    private record HoveredNode(SkillTreeCategory category, SkillTreeNode node) {
    }

    /**
     * Finds the node closest to (screen) {@code mouseX}/{@code mouseY} whose
     * hit-radius contains the cursor (in tree-space, so it respects the
     * current pan/zoom) - shared by {@link #render}'s hover highlight/tooltip
     * and {@link #mouseClicked}'s click-to-unlock, so the two can never
     * disagree about what's "under the cursor".
     */
    private HoveredNode findHovered(double mouseX, double mouseY) {
        double[] mouseTree = screenToTree(mouseX, mouseY);
        SkillTreeCategory bestCategory = null;
        SkillTreeNode bestNode = null;
        double bestDistSq = Double.MAX_VALUE;
        for (SkillTreeCategory category : ClientSkillTreeState.get().categoriesSorted()) {
            for (SkillTreeNode node : category.nodes()) {
                double dx = node.x() - mouseTree[0];
                double dy = node.y() - mouseTree[1];
                double distSq = dx * dx + dy * dy;
                float halfSize = node.root() ? ROOT_NODE_HALF_SIZE : NODE_HALF_SIZE;
                if (distSq <= (halfSize * halfSize) && distSq < bestDistSq) {
                    bestDistSq = distSq;
                    bestNode = node;
                    bestCategory = category;
                }
            }
        }
        return bestNode == null ? null : new HoveredNode(bestCategory, bestNode);
    }

    @Override
    public boolean mouseClicked(double mouseX, double mouseY, int button) {
        if (super.mouseClicked(mouseX, mouseY, button)) {
            return true;
        }
        if (button != 0) {
            return false;
        }
        HoveredNode hoveredNode = findHovered(mouseX, mouseY);
        if (hoveredNode == null) {
            return false;
        }
        NodeVisualState state = NodeVisualState.of(hoveredNode.node(), hoveredNode.category(), ClientSkillTreeState.progress());
        if (state == NodeVisualState.AVAILABLE) {
            // The server is the sole authority on whether this actually succeeds -
            // see server.ServerSkillEvents#handleUnlockRequest. This click only ever
            // sends the request; ClientSkillTreeState's mirror updates once the
            // server's SkillProgressSyncPayload response arrives.
            PacketDistributor.sendToServer(new SkillUnlockRequestPayload(hoveredNode.category().id(), hoveredNode.node().id()));
        }
        return true;
    }

    /**
     * Quadratic Bezier from (x1,y1) to (x2,y2) with a control point offset
     * perpendicular to the segment (a PoE-style gentle arc rather than a
     * straight prerequisite line), sampled into {@value #CURVE_SEGMENTS}
     * {@link #drawThickSegment} calls.
     */
    private void drawCurve(GuiGraphics graphics, double x1, double y1, double x2, double y2, int color) {
        double dx = x2 - x1;
        double dy = y2 - y1;
        double length = Math.sqrt(dx * dx + dy * dy);
        double bow = Math.min(length * 0.12, 18.0);
        double midX = (x1 + x2) / 2.0;
        double midY = (y1 + y2) / 2.0;
        double controlX = midX;
        double controlY = midY;
        if (length > 1.0e-4) {
            // Perpendicular unit vector, scaled by the bow amount.
            controlX += (-dy / length) * bow;
            controlY += (dx / length) * bow;
        }

        double prevX = x1;
        double prevY = y1;
        for (int i = 1; i <= CURVE_SEGMENTS; i++) {
            double t = (double) i / CURVE_SEGMENTS;
            double omt = 1.0 - t;
            double px = omt * omt * x1 + 2 * omt * t * controlX + t * t * x2;
            double py = omt * omt * y1 + 2 * omt * t * controlY + t * t * y2;
            drawThickSegment(graphics, prevX, prevY, px, py, color);
            prevX = px;
            prevY = py;
        }
    }

    /**
     * Draws a filled rectangle from (x1,y1) to (x2,y2) at {@link #LINE_THICKNESS}
     * wide, via a nested pose rotated to the segment's angle - see the class
     * doc for why this stands in for a real line primitive.
     */
    private void drawThickSegment(GuiGraphics graphics, double x1, double y1, double x2, double y2, int color) {
        double dx = x2 - x1;
        double dy = y2 - y1;
        double length = Math.sqrt(dx * dx + dy * dy);
        if (length < 1.0e-4) {
            return;
        }
        float angle = (float) Math.atan2(dy, dx);

        PoseStack pose = graphics.pose();
        pose.pushPose();
        pose.translate((x1 + x2) / 2.0, (y1 + y2) / 2.0, 0);
        pose.mulPose(new Quaternionf().rotationZ(angle));
        float half = (float) (length / 2.0);
        graphics.fill((int) -half, (int) (-LINE_THICKNESS / 2), (int) half, (int) (LINE_THICKNESS / 2), color);
        pose.popPose();
    }

    private double[] screenToTree(double screenX, double screenY) {
        double treeX = (screenX - originScreenX - panX) / zoom;
        double treeY = (screenY - originScreenY - panY) / zoom;
        return new double[]{treeX, treeY};
    }

    @Override
    public boolean mouseDragged(double mouseX, double mouseY, int button, double dragX, double dragY) {
        if (super.mouseDragged(mouseX, mouseY, button, dragX, dragY)) {
            return true;
        }
        panX += (float) dragX;
        panY += (float) dragY;
        return true;
    }

    @Override
    public boolean mouseScrolled(double mouseX, double mouseY, double scrollX, double scrollY) {
        if (super.mouseScrolled(mouseX, mouseY, scrollX, scrollY)) {
            return true;
        }
        if (scrollY == 0) {
            return false;
        }
        double[] treeUnderCursor = screenToTree(mouseX, mouseY);
        float factor = scrollY > 0 ? 1.15f : 1 / 1.15f;
        float newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom * factor));
        // Re-anchor pan so the tree point currently under the cursor stays
        // under the cursor after the zoom change, instead of zooming toward
        // the canvas origin.
        panX = (float) (mouseX - originScreenX - treeUnderCursor[0] * newZoom);
        panY = (float) (mouseY - originScreenY - treeUnderCursor[1] * newZoom);
        zoom = newZoom;
        return true;
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }
}
