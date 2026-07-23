package dev.vanillaplusplus.vppquests.quest;

import dev.vanillaplusplus.vppquests.VppQuests;
import dev.vanillaplusplus.vppquests.data.ModAttachments;
import dev.vanillaplusplus.vppquests.data.QuestProgressAttachment;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.storage.LevelResource;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * DESIGN.md's #109 Phase B: one-time, idempotent identity-mapping migration
 * from the legacy KubeJS quest tracker ({@code pack/kubejs/server_scripts/
 * quests.js}) into this mod's {@link QuestProgressAttachment}, run on a
 * player's first login after this mod is installed. Deliberately an
 * identity mapping (same quest ids, no re-interpretation) per the design's
 * own phasing - the heuristic re-mapping for a rebuilt questline is Phase D,
 * not this class.
 *
 * <p><b>Where the legacy data lives (ground-truthed, not guessed):</b>
 * {@code quests.js}'s {@code questsProgressCompound()} reads/writes
 * {@code server.persistentData}, a KubeJS-mixed-in field on
 * {@code MinecraftServer} (see {@code MinecraftServerMixin}). That field is
 * round-tripped to disk by KubeJS's own {@code KubeJSServerEventHandler},
 * confirmed via jar inspection of the pinned
 * {@code kubejs-neoforge-2101.7.2-build.368.jar}: it registers
 * {@code PERSISTENT_DATA = new LevelResource("kubejs_persistent_data.nbt")}
 * and reads/writes it with vanilla's own {@code NbtIo.readCompressed}/
 * {@code writeCompressed} on {@code LevelEvent.Load}/{@code Save} - i.e. a
 * single compressed NBT file at
 * {@code <world save>/kubejs_persistent_data.nbt}, resolved the same way
 * {@link MinecraftServer#getWorldPath(LevelResource)} resolves any other
 * root-level save file (e.g. {@code level.dat}). No separate KubeJS
 * dependency is needed in this standalone mod to read it - it's a plain
 * vanilla-NBT file.
 *
 * <p><b>Known Phase B limitation (disclosed, not an oversight):</b> only
 * quests.js's per-player fallback progress key ({@code "player:" + uuid})
 * is migrated here. quests.js also supports a team-shared key
 * ({@code "team:" + partyId}, via Open Parties and Claims - see its
 * {@code getProgressKey()}) but this mod's {@link QuestProgressAttachment}
 * is itself Phase-A-scoped to per-player storage only (that class's own doc
 * comment flags the same {@code getPartyKey(player)} re-key GitHub #32
 * already proved out for {@code quests.js} as future work). Until a later
 * phase wires that seam here too, players who progressed via a shared team
 * key will not have that progress migrated - a UX regression (they can
 * simply re-complete those quests) but never a correctness bug, since no
 * reward is ever double-granted either way (a migrated quest is marked
 * complete before this mod's own tracker ever sees it, so
 * {@link QuestProgressTracker} skips reward-granting for it exactly like
 * any other already-complete quest).
 */
public final class QuestLegacyMigration {

    private static final LevelResource LEGACY_PERSISTENT_DATA_FILE = new LevelResource("kubejs_persistent_data.nbt");
    /** Same {@code QUESTS_PROGRESS_ROOT_KEY} constant quests.js itself uses. */
    private static final String LEGACY_ROOT_KEY = "vpp_quests_progress";
    /** NBT compound-tag type id, same constant quests.js's own {@code questsEnsureCompound} comments. */
    private static final int NBT_COMPOUND_TAG_ID = 10;

    private static volatile CompoundTag cachedLegacyRoot;
    private static volatile boolean cacheLoaded = false;

    private QuestLegacyMigration() {
    }

    /** Resets the per-server-process cache - call on server stopping so a later server start re-reads the file. */
    public static void resetCache() {
        cacheLoaded = false;
        cachedLegacyRoot = null;
    }

    public static void migrate(ServerPlayer player) {
        QuestProgressAttachment attachment = player.getData(ModAttachments.QUEST_PROGRESS);
        if (attachment.isLegacyMigrated()) {
            return;
        }

        CompoundTag legacyPlayerProgress = legacyProgressFor(player);
        int migratedCount = 0;
        if (legacyPlayerProgress != null) {
            for (String questIdKey : legacyPlayerProgress.getAllKeys()) {
                if (!legacyPlayerProgress.getBoolean(questIdKey)) {
                    continue;
                }
                ResourceLocation questId = ResourceLocation.tryParse(questIdKey);
                if (questId != null && QuestRegistry.get().quest(questId).isPresent() && !attachment.isComplete(questId)) {
                    attachment.markComplete(questId);
                    migratedCount++;
                }
            }
        }

        attachment.markLegacyMigrated();
        if (migratedCount > 0) {
            VppQuests.LOGGER.info(
                    "vppquests: Phase B migration - carried forward {} already-complete legacy quest(s) for {}",
                    migratedCount, player.getGameProfile().getName());
        }
    }

    private static CompoundTag legacyProgressFor(ServerPlayer player) {
        CompoundTag root = legacyRoot(player.getServer());
        if (root == null) {
            return null;
        }
        String legacyPlayerKey = "player:" + player.getUUID();
        if (!root.contains(legacyPlayerKey, NBT_COMPOUND_TAG_ID)) {
            return null;
        }
        return root.getCompound(legacyPlayerKey);
    }

    /**
     * Lazily reads and caches the legacy save file for the lifetime of this
     * server process - quests.js is only removed at Phase C (after this
     * migration is confirmed stable), so the file's contents can't change
     * mid-session from anything other than quests.js itself running
     * alongside this mod; re-reading per login is unneeded I/O.
     */
    private static CompoundTag legacyRoot(MinecraftServer server) {
        if (cacheLoaded) {
            return cachedLegacyRoot;
        }
        synchronized (QuestLegacyMigration.class) {
            if (cacheLoaded) {
                return cachedLegacyRoot;
            }
            CompoundTag result = null;
            Path path = server.getWorldPath(LEGACY_PERSISTENT_DATA_FILE);
            try {
                if (Files.exists(path)) {
                    CompoundTag fileRoot = NbtIo.readCompressed(path, NbtAccounter.unlimitedHeap());
                    if (fileRoot.contains(LEGACY_ROOT_KEY, NBT_COMPOUND_TAG_ID)) {
                        result = fileRoot.getCompound(LEGACY_ROOT_KEY);
                    }
                } else {
                    VppQuests.LOGGER.info(
                            "vppquests: no legacy quests.js save file found at {} (new world, or old system never installed) - Phase B migration is a no-op",
                            path);
                }
            } catch (IOException e) {
                VppQuests.LOGGER.error(
                        "vppquests: failed to read legacy quests.js save file at {} - Phase B migration skipped this session",
                        path, e);
            }
            cachedLegacyRoot = result;
            cacheLoaded = true;
            return cachedLegacyRoot;
        }
    }
}
