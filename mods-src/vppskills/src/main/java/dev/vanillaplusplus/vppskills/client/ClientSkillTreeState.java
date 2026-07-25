package dev.vanillaplusplus.vppskills.client;

import dev.vanillaplusplus.vppskills.tree.SkillTreeData;
import dev.vanillaplusplus.vppskills.tree.SkillTreeLoader;
import net.minecraft.client.Minecraft;

/**
 * Lazily loads and caches the ported {@link SkillTreeData} on first use
 * (opening the debug screen), rather than eagerly on mod construction -
 * {@link Minecraft#getInstance()}'s {@code ResourceManager} isn't
 * guaranteed populated with every mod's assets that early. No live-reload
 * hook yet (see {@code SkillTreeLoader}'s class doc); call
 * {@link #invalidate()} and re-open the screen to force a re-read after a
 * jar rebuild during dev iteration.
 */
public final class ClientSkillTreeState {

    private static SkillTreeData data;

    public static SkillTreeData get() {
        if (data == null) {
            data = SkillTreeLoader.load(Minecraft.getInstance().getResourceManager());
        }
        return data;
    }

    public static void invalidate() {
        data = null;
    }

    private ClientSkillTreeState() {
    }
}
