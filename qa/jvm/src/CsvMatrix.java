import android.content.res.Resources;
import com.kidslock.app.QuestionBank;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

/** CSV 跨平台矩阵 - Android 侧 */
public class CsvMatrix {
    static int p = 0, f = 0;
    static void check(String name, boolean ok, String detail) {
        System.out.println((ok ? "PASS" : "FAIL") + " | " + name + (detail.isEmpty() ? "" : " | " + detail));
        if (ok) p++; else f++;
    }

    static int s = 0;
    static void skip(String name, String why) {
        s++;
        System.out.println("SKIP | " + name + " | " + why);
    }

    public static void main(String[] args) throws Exception {
        java.nio.file.Path qJson = QaPaths.androidQuestions();
        java.nio.file.Path tmpDir = QaPaths.qaTmp();
        Resources.setRawPath(qJson.toString());
        new java.io.File(System.getProperty("kidslock.filedir", "filedir"), "custom_banks.json").delete();
        QuestionBank qb = new QuestionBank(new TestCtx());
        JSONObject J = new JSONObject(new String(Files.readAllBytes(qJson), StandardCharsets.UTF_8));

        // 导出供鸿蒙侧导入
        java.nio.file.Path adExport = tmpDir.resolve("ad_export_math_g9.csv");
        Files.write(adExport, qb.exportCsv("math_g9").getBytes(StandardCharsets.UTF_8));

        // M4: Android 导入鸿蒙导出（无引号转义的 math_g9）
        java.nio.file.Path hmExport = tmpDir.resolve("hm_export_math_g9.csv");
        if (!Files.exists(hmExport)) {
            skip("M4 Android 导入鸿蒙导出 math_g9", "缺少 qa/tmp/hm_export_math_g9.csv（先在鸿蒙侧导出，见 qa/README.md）");
        } else try {
            String hm = new String(Files.readAllBytes(hmExport), StandardCharsets.UTF_8);
            int n = qb.bankSize(qb.importCsv("fromHarmony", hm));
            int expect = J.getJSONObject("banks").getJSONArray("math_g9").length();
            int intact = 0;
            for (int s = 0; s < 500; s++) {
                String t = qb.getQuestion("custom_fromHarmony").text;
                org.json.JSONArray arr = J.getJSONObject("banks").getJSONArray("math_g9");
                for (int j = 0; j < arr.length(); j++) {
                    if (arr.getJSONObject(j).getString("q").equals(t)) { intact++; break; }
                }
            }
            java.util.Set<String> seen = new java.util.HashSet<>();
            for (int s = 0; s < 500; s++) seen.add(qb.getQuestion("custom_fromHarmony").text);
            int distinctIntact = 0;
            for (String t : seen) {
                org.json.JSONArray arr = J.getJSONObject("banks").getJSONArray("math_g9");
                for (int j = 0; j < arr.length(); j++) {
                    if (arr.getJSONObject(j).getString("q").equals(t)) { distinctIntact++; break; }
                }
            }
            check("M4 Android 导入鸿蒙导出 math_g9", n == expect && distinctIntact == expect,
                    String.format("n=%d/%d 完整题干=%d/%d", n, expect, distinctIntact, expect));
        } catch (Exception e) {
            check("M4 Android 导入鸿蒙导出 math_g9", false, e.getMessage());
        }

        // M5: Android 导入官方种子 math_g10.csv（生成器无引号转义）
        java.nio.file.Path seedCsv = QaPaths.repoRoot().resolve("dist/csv/math_g10.csv");
        if (!Files.exists(seedCsv)) {
            skip("M5 Android 导入官方种子 math_g10.csv", "缺少 dist/csv/math_g10.csv（先运行 python scripts/gen_question_banks.py）");
        } else try {
            String seed = new String(Files.readAllBytes(seedCsv), StandardCharsets.UTF_8);
            int n = qb.bankSize(qb.importCsv("fromSeed", seed));
            int expect = J.getJSONObject("banks").getJSONArray("math_g10").length();
            java.util.Set<String> seen = new java.util.HashSet<>();
            for (int s = 0; s < 500; s++) seen.add(qb.getQuestion("custom_fromSeed").text);
            int distinctIntact = 0;
            for (String t : seen) {
                org.json.JSONArray arr = J.getJSONObject("banks").getJSONArray("math_g10");
                for (int j = 0; j < arr.length(); j++) {
                    if (arr.getJSONObject(j).getString("q").equals(t)) { distinctIntact++; break; }
                }
            }
            check("M5 Android 导入官方种子 math_g10.csv", n == expect && distinctIntact == expect,
                    String.format("n=%d/%d 完整题干=%d/%d", n, expect, distinctIntact, expect));
        } catch (Exception e) {
            check("M5 Android 导入官方种子 math_g10.csv", false, e.getMessage());
        }

        System.out.println("===== CSV矩阵-Android侧: " + p + " PASS / " + f + " FAIL / " + s + " SKIP =====");
        if (f > 0) System.exit(1);
    }

    static class TestCtx extends android.content.Context {}
}
