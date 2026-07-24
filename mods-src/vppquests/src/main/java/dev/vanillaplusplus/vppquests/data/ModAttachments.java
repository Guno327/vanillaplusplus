package dev.vanillaplusplus.vppquests.data;

import dev.vanillaplusplus.vppquests.VppQuests;
import net.neoforged.neoforge.attachment.AttachmentType;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.neoforged.neoforge.registries.NeoForgeRegistries;

/**
 * Registers this mod's single {@link QuestProgressAttachment} data
 * attachment type - the NeoForge 1.20.5+/1.21 replacement for the old Forge
 * capability system, per DESIGN.md's #109 design-proposal section.
 */
public final class ModAttachments {

    public static final DeferredRegister<AttachmentType<?>> ATTACHMENT_TYPES =
            DeferredRegister.create(NeoForgeRegistries.Keys.ATTACHMENT_TYPES, VppQuests.MODID);

    public static final DeferredHolder<AttachmentType<?>, AttachmentType<QuestProgressAttachment>> QUEST_PROGRESS =
            ATTACHMENT_TYPES.register("quest_progress", () -> AttachmentType.builder(QuestProgressAttachment::new)
                    .serialize(QuestProgressAttachment.CODEC)
                    .build());

    private ModAttachments() {
    }
}
