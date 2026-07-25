package dev.vanillaplusplus.vppskills.client;

import dev.vanillaplusplus.vppskills.data.SkillProgressAttachment;
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
 *
 * <p>Also holds the local player's {@link SkillProgressAttachment} mirror,
 * kept up to date by {@code network.ModNetworking}'s
 * {@code SkillProgressSyncPayload} handler - same
 * "server pushes, client only ever reads a cached mirror, never round-trips
 * per frame" pattern {@code vppquests}' {@code ClientQuestState} already
 * proved for quest progress. {@code client.gui.SkillTreeScreen} does not read
 * {@link #progress()} yet (per #163 phase-2 scope: click-to-unlock wiring
 * is a follow-up, not this phase - see {@code network.ModNetworking}'s
 * class doc), but the mirror is populated from the moment a
 * {@code SkillProgressSyncPayload} first arrives.
 */
public final class ClientSkillTreeState {

    private static SkillTreeData data;
    private static volatile SkillProgressAttachment progress = new SkillProgressAttachment();

    public static SkillTreeData get() {
        if (data == null) {
            data = SkillTreeLoader.load(Minecraft.getInstance().getResourceManager());
        }
        return data;
    }

    public static void invalidate() {
        data = null;
    }

    /** Invoked by {@code network.ModNetworking}'s payload handler whenever a {@code SkillProgressSyncPayload} arrives. */
    public static void applyProgress(String progressJson) {
        progress = SkillProgressAttachment.fromJson(progressJson);
    }

    /** The local player's last-synced skill progress mirror (unlocked nodes, available/spent points). */
    public static SkillProgressAttachment progress() {
        return progress;
    }

    private ClientSkillTreeState() {
    }
}
