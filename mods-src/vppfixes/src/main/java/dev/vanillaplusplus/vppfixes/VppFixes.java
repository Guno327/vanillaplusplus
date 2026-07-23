package dev.vanillaplusplus.vppfixes;

import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Vanilla++ Fixes: a small home for hand-rolled, pack-specific correctness fixes to
 * third-party mods that can only be expressed as bytecode (Mixin) rather than config
 * or datapack overrides. Custom mods are an owner-approved exception to the pack's
 * No-New-Mods rule, tracked separately under {@code mods-src/} (this is the pack's
 * third, after vppintegration and vppquests).
 *
 * <p><b>First and only fix so far (GitHub #143):</b> Ars Nouveau crashes the entity-data
 * network path with a {@link java.util.ConcurrentModificationException}. Ars registers
 * its {@code ars_nouveau:spell_resolver} {@link net.minecraft.network.syncher.EntityDataSerializer}
 * via {@code EntityDataSerializer.forValueType(SpellResolver.STREAM)}, whose {@code copy(T)}
 * is the identity function. It then stores a live, mutable {@code SpellResolver} object
 * graph (Spell -&gt; recipe list + Optional&lt;TimelineMap&gt; particle-timeline, encoded by a
 * DFU {@code Codec} through NBT) as {@link net.minecraft.network.syncher.SynchedEntityData}
 * on {@code EntityProjectileSpell}/{@code EntitySpellArrow}. Because {@code copy()} is
 * identity, the value the entity-tracker packs is the SAME object the server tick thread
 * keeps mutating. The tracker then serializes that live graph on the Netty IO thread
 * ({@code SynchedEntityData$DataValue.write}), so a main-thread list mutation races the
 * IO-thread {@code ListCodec.encode} iteration and throws CME, failing to encode
 * {@code clientbound/minecraft:set_entity_data} and disconnecting the tracking client
 * ("Internal Exception"). Spell arrows stick in the ground and persist, so the race
 * recurs periodically.
 *
 * <p><b>The fix</b> lives entirely in {@link dev.vanillaplusplus.vppfixes.mixin.SynchedEntityDataMixin}
 * + {@link SynchedDataSnapshots}: it takes a genuine deep copy of the offending value at
 * pack time (which runs on the server tick/main thread, see that class' doc) so the IO
 * thread only ever encodes an immutable snapshot that nothing mutates. It is keyed on the
 * serializer's registry id string, so it carries NO compile-time dependency on Ars Nouveau
 * and degrades to a harmless pass-through if that serializer is absent.
 */
@Mod(VppFixes.MODID)
public final class VppFixes {
    public static final String MODID = "vppfixes";
    public static final Logger LOGGER = LoggerFactory.getLogger("VanillaPlusPlus-Fixes");

    public VppFixes(IEventBus modEventBus, ModContainer modContainer) {
        LOGGER.info("vppfixes loaded: entity-data CME guard active (GitHub #143)");
    }
}
