package dev.vanillaplusplus.vppskills.data;

import dev.vanillaplusplus.vppskills.VppSkills;
import net.neoforged.neoforge.attachment.AttachmentType;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.neoforged.neoforge.registries.NeoForgeRegistries;

/**
 * Registers this mod's single {@link SkillProgressAttachment} data
 * attachment type - mirrors {@code vppquests}' {@code ModAttachments}
 * exactly (same {@code DeferredRegister}/{@code AttachmentType.builder}
 * shape, same NeoForge 1.20.5+/1.21 capability-system replacement).
 */
public final class ModAttachments {

    public static final DeferredRegister<AttachmentType<?>> ATTACHMENT_TYPES =
            DeferredRegister.create(NeoForgeRegistries.Keys.ATTACHMENT_TYPES, VppSkills.MODID);

    public static final DeferredHolder<AttachmentType<?>, AttachmentType<SkillProgressAttachment>> SKILL_PROGRESS =
            ATTACHMENT_TYPES.register("skill_progress", () -> AttachmentType.builder(SkillProgressAttachment::new)
                    .serialize(SkillProgressAttachment.CODEC)
                    .build());

    private ModAttachments() {
    }
}
