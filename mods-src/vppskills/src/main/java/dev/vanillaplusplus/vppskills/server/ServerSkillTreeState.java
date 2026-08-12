package dev.vanillaplusplus.vppskills.server;

import dev.vanillaplusplus.vppskills.tree.SkillTreeData;
import dev.vanillaplusplus.vppskills.tree.SkillTreeLoader;

/**
 * Server-side mirror of {@code client.ClientSkillTreeState}'s tree-data
 * cache: lazily loads and caches the same ported {@link SkillTreeData} the
 * client renders, so {@link ServerSkillEvents}' unlock handler can look up
 * the category/node a request refers to and validate it
 * ({@code unlock.SkillUnlockValidator}) without trusting anything the client
 * sent about the tree's shape.
 *
 * <p>Uses {@link SkillTreeLoader#loadFromClasspath} rather than
 * {@link SkillTreeLoader#load} - see that method's doc: a dedicated server
 * has no client {@code ResourceManager} for {@code assets/} paths, but this
 * mod's own jar has the same data baked in as a plain classpath resource
 * (via {@code build.gradle}'s {@code importSkillTreeData} task), which a
 * {@link ClassLoader} read reaches identically on either side.
 */
public final class ServerSkillTreeState {

    private static volatile SkillTreeData data;

    public static SkillTreeData get() {
        SkillTreeData local = data;
        if (local == null) {
            synchronized (ServerSkillTreeState.class) {
                local = data;
                if (local == null) {
                    local = SkillTreeLoader.loadFromClasspath(ServerSkillTreeState.class.getClassLoader());
                    data = local;
                }
            }
        }
        return local;
    }

    private ServerSkillTreeState() {
    }
}
