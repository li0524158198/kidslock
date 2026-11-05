import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/** qa/jvm 公共路径：仓库根自动探测，可用 -Dkidslock.root=<仓库根> 覆盖（run 脚本会传）。 */
public final class QaPaths {
    private QaPaths() {
    }

    /** 仓库根：优先系统属性；否则从当前目录向上找 data/questions.json（qa/jvm 向上两级）。 */
    public static Path repoRoot() {
        String prop = System.getProperty("kidslock.root");
        if (prop != null && !prop.isEmpty()) {
            return Paths.get(prop).toAbsolutePath().normalize();
        }
        Path p = Paths.get("").toAbsolutePath();
        for (int i = 0; i < 6 && p != null; i++, p = p.getParent()) {
            if (Files.isRegularFile(p.resolve("data").resolve("questions.json"))) {
                return p;
            }
        }
        throw new IllegalStateException(
                "找不到仓库根（data/questions.json）：请在 qa/jvm 目录运行，或用 -Dkidslock.root=<仓库根> 指定");
    }

    /** Android 生产资源里的题库（JVM 测试直接加载它，保证测的就是 APK 里带的；与单一源一致性由 sync_questions.py --check 保证）。 */
    public static Path androidQuestions() {
        return repoRoot().resolve("kidslock-src/app/src/main/res/raw/questions.json");
    }

    /** 测试 scratch 目录（跨平台 CSV 矩阵的输入输出），不存在则创建。 */
    public static Path qaTmp() {
        Path p = repoRoot().resolve("qa").resolve("tmp");
        try {
            Files.createDirectories(p);
        } catch (java.io.IOException e) {
            throw new RuntimeException(e);
        }
        return p;
    }
}
