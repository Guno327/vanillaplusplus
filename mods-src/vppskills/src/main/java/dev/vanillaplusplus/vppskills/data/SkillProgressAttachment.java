package dev.vanillaplusplus.vppskills.data;

import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.mojang.serialization.Codec;
import com.mojang.serialization.JsonOps;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import dev.vanillaplusplus.vppskills.VppSkills;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Per-player skill-tree progress: unlocked node ids plus the point economy
 * (available/spent), persisted via a NeoForge data attachment on the player
 * entity - the phase-2 (#163) analogue of {@code vppquests}'
 * {@code QuestProgressAttachment}, same shape and same rationale (data
 * attachments are the modern capability-system replacement).
 *
 * <p><b>Scope note (mirrors {@code QuestProgressAttachment}'s):</b> progress
 * is attached to the player entity directly (solo-player semantics only). No
 * party-shared unlock mode is implemented.
 *
 * <p>Mutation only ever happens through {@code unlock}/{@code respec} so
 * every caller (currently {@link dev.vanillaplusplus.vppskills.unlock.SkillUnlockValidator})
 * goes through the same debit/credit bookkeeping - there is no direct setter
 * for {@link #availablePoints} or the unlocked set.
 */
public final class SkillProgressAttachment {

    private final Set<String> unlockedNodes = new HashSet<>();
    private int availablePoints;
    private int spentPoints;

    public boolean isUnlocked(String nodeId) {
        return unlockedNodes.contains(nodeId);
    }

    public Set<String> unlockedNodeIds() {
        return Set.copyOf(unlockedNodes);
    }

    public int availablePoints() {
        return availablePoints;
    }

    public int spentPoints() {
        return spentPoints;
    }

    /**
     * Grants unspent points to the player (e.g. from a future XP-source
     * hook - out of scope for this phase per #163's brief, which explicitly
     * excludes XP-source point-granting). Exposed now so the point economy
     * has a single, obvious seam for that later phase to call into.
     */
    public void grantPoints(int amount) {
        availablePoints += amount;
    }

    /**
     * Debits {@code cost} points and marks {@code nodeId} unlocked. Callers
     * MUST have already validated the request (adjacency, not-already-unlocked,
     * sufficient points) via {@link dev.vanillaplusplus.vppskills.unlock.SkillUnlockValidator} -
     * this method does no validation itself, it only performs the bookkeeping
     * a validated unlock requires.
     */
    public void unlock(String nodeId, int cost) {
        unlockedNodes.add(nodeId);
        availablePoints -= cost;
        spentPoints += cost;
    }

    /**
     * Reverses a single node's unlock and refunds its cost - the respec
     * building block a later phase's respec command/UI will call
     * (attribute-modifier removal is a separate concern, see
     * {@link dev.vanillaplusplus.vppskills.reward.AttributeOperationTranslator}'s
     * class doc for the reverse/clear path). No-op if the node wasn't
     * unlocked.
     */
    public void respec(String nodeId, int refund) {
        if (unlockedNodes.remove(nodeId)) {
            availablePoints += refund;
            spentPoints -= refund;
        }
    }

    public static final Codec<SkillProgressAttachment> CODEC = RecordCodecBuilder.create(instance -> instance.group(
            Codec.STRING.listOf().fieldOf("unlockedNodes").forGetter(a -> List.copyOf(a.unlockedNodes)),
            Codec.INT.fieldOf("availablePoints").forGetter(a -> a.availablePoints),
            Codec.INT.fieldOf("spentPoints").forGetter(a -> a.spentPoints)
    ).apply(instance, (unlockedList, available, spent) -> {
        SkillProgressAttachment attachment = new SkillProgressAttachment();
        attachment.unlockedNodes.addAll(unlockedList);
        attachment.availablePoints = available;
        attachment.spentPoints = spent;
        return attachment;
    }));

    /**
     * Re-uses {@link #CODEC} (the source of truth for this attachment's NBT
     * persistence) to produce the JSON string
     * {@code SkillProgressSyncPayload} sends to the owning client, so the
     * network wire format and the save-data format can never drift apart -
     * same technique {@code QuestProgressAttachment#toJson} already proved.
     */
    public String toJson() {
        return CODEC.encodeStart(JsonOps.INSTANCE, this)
                .resultOrPartial(error -> VppSkills.LOGGER.error("vppskills: failed to encode skill progress: {}", error))
                .map(JsonElement::toString)
                .orElse("{}");
    }

    public static SkillProgressAttachment fromJson(String json) {
        JsonElement element = JsonParser.parseString(json);
        return CODEC.parse(JsonOps.INSTANCE, element)
                .resultOrPartial(error -> VppSkills.LOGGER.error("vppskills: failed to decode skill progress: {}", error))
                .orElseGet(SkillProgressAttachment::new);
    }
}
