import android.content.SharedPreferences;
import android.content.res.Resources;
import com.kidslock.app.PrefManager;
import com.kidslock.app.QuestionBank;
import org.json.JSONObject;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** T4: Android 真实源码（QuestionBank.java / PrefManager.java）JVM 逻辑测试 */
public class JvmTests {
    static int p = 0, f = 0;
    static final StringBuilder fails = new StringBuilder();

    static void check(String name, boolean ok, String... detailArr) {
        String detail = detailArr.length > 0 ? detailArr[0] : "";
        System.out.println((ok ? "PASS" : "FAIL") + " | " + name + (detail.isEmpty() ? "" : " | " + detail));
        if (ok) p++; else { f++; fails.append("  - ").append(name).append(detail.isEmpty() ? "" : " | " + detail).append('\n'); }
    }

    static JSONObject jsonData;

    public static void main(String[] args) throws Exception {
        // 路径统一走 QaPaths（-Dkidslock.root 覆盖，默认从当前目录向上探测仓库根）
        java.nio.file.Path qJson = QaPaths.androidQuestions();
        String json = new String(Files.readAllBytes(qJson), StandardCharsets.UTF_8);
        jsonData = new JSONObject(json);
        Resources.setRawPath(qJson.toString());
        // 清理旧的持久化文件（保证测试隔离）
        new java.io.File(System.getProperty("kidslock.filedir", "filedir"), "custom_banks.json").delete();

        TestContext ctx = new TestContext();
        QuestionBank qb = new QuestionBank(ctx);

        // ================= PrefManager =================
        prefTests();

        // ================= QuestionBank =================
        // T4.10 内置库清单
        List<QuestionBank.BankItem> banks = qb.getBankList();
        check("T4.10 题库清单含 36 内置库", banks.size() == 36 && banks.stream().filter(b -> !b.custom).count() == 36,
                "size=" + banks.size());
        check("T4.10b 清单 id/label 样例", banks.get(0).id.equals("chinese_g1") && banks.get(35).id.equals("english_g12")
                && banks.get(11).label.equals("语文·高三"), banks.get(0).id + "," + banks.get(11).label);

        // T4.11 resolveBankId 兼容
        check("T4.11a primary→g5", qb.resolveBankId("math_primary").equals("math_g5"));
        check("T4.11b junior→g7", qb.resolveBankId("chinese_junior").equals("chinese_g7"));
        check("T4.11c senior→g10", qb.resolveBankId("english_senior").equals("english_g10"));
        check("T4.11d 非法→chinese_g1", qb.resolveBankId("nope").equals("chinese_g1"));
        check("T4.11e null→chinese_g1", qb.resolveBankId(null).equals("chinese_g1"));

        // T4.12 内置出题：答案索引一致性（对数据标答）
        {
            int bad = 0; String sample = "";
            for (String id : jsonData.getJSONObject("banks").keySet()) {
                java.util.Map<String, String> amap = new java.util.HashMap<>();
                org.json.JSONArray arr = jsonData.getJSONObject("banks").getJSONArray(id);
                for (int i = 0; i < arr.length(); i++) {
                    JSONObject it = arr.getJSONObject(i);
                    amap.put(it.getString("q"), it.getJSONArray("opts").getString(it.getInt("ans")));
                }
                for (int i = 0; i < 30; i++) {
                    QuestionBank.Question q = qb.getQuestion(id);
                    if (q.options.size() != 4 || q.answerIndex < 0 || q.answerIndex > 3) { bad++; continue; }
                    String expect = amap.get(q.text);
                    if (expect != null && !q.options.get(q.answerIndex).equals(expect)) {
                        bad++;
                        if (sample.isEmpty()) sample = id + ": " + q.text + " 选中=" + q.options.get(q.answerIndex) + " 数据标答=" + expect;
                    }
                }
            }
            check("T4.12 内置库出题 1080 次：与数据标答一致", bad == 0, sample);
        }

        // T4.13 genMath 隔离测试（反射调用私有方法，排除内置坏数据干扰）
        {
            java.lang.reflect.Method gen = QuestionBank.class.getDeclaredMethod("genMath", int.class);
            gen.setAccessible(true);
            int mulBad = 0, mulTotal = 0, otherBad = 0, negDistractor = 0, dupOpt = 0, negAnswer = 0;
            String mulSample = "", otherSample = "";
            final char MULCH = 215; // ×
            final char DIVCH = 247; // ÷
            java.util.regex.Pattern p3 = java.util.regex.Pattern.compile("([0-9]+) [+] ([0-9]+) - ([0-9]+) = [?]$");
            java.util.regex.Pattern pe = java.util.regex.Pattern.compile("解方程：([0-9]+)x [+] ([0-9]+) = ([0-9]+)，x = [?]$");
            java.util.regex.Pattern mulPat = java.util.regex.Pattern.compile("([0-9]+) [" + MULCH + "] ([0-9]+) = [?]$");
            java.util.regex.Pattern divPat = java.util.regex.Pattern.compile("([0-9]+) [" + DIVCH + "] ([0-9]+) = [?]$");
            java.util.regex.Pattern addPat = java.util.regex.Pattern.compile("([0-9]+) [+] ([0-9]+) = [?]$");
            java.util.regex.Pattern subPat = java.util.regex.Pattern.compile("([0-9]+) [-] ([0-9]+) = [?]$");
            for (int g = 1; g <= 9; g++) {
                for (int i = 0; i < 3000; i++) {
                    QuestionBank.Question q = (QuestionBank.Question) gen.invoke(qb, g);
                    if (q == null) { otherBad++; otherSample = "g" + g + " null"; continue; }
                    if (new HashSet<>(q.options).size() != 4) dupOpt++;
                    for (int oi = 0; oi < q.options.size(); oi++) {
                        if (q.options.get(oi).startsWith("-") && oi != q.answerIndex) negDistractor++;
                    }
                    if (q.options.get(q.answerIndex).startsWith("-")) negAnswer++;
                    long expect; java.util.regex.Matcher m;
                    if ((m = p3.matcher(q.text)).matches()) {
                        expect = Long.parseLong(m.group(1)) + Long.parseLong(m.group(2)) - Long.parseLong(m.group(3));
                        if (Long.parseLong(q.options.get(q.answerIndex)) != expect) { otherBad++; if (otherSample.isEmpty()) otherSample = q.text; }
                    } else if ((m = pe.matcher(q.text)).matches()) {
                        expect = (Long.parseLong(m.group(3)) - Long.parseLong(m.group(2))) / Long.parseLong(m.group(1));
                        if (Long.parseLong(q.options.get(q.answerIndex)) != expect) { otherBad++; if (otherSample.isEmpty()) otherSample = q.text; }
                    } else if (q.text.indexOf(MULCH) >= 0 && (m = mulPat.matcher(q.text)).matches()) {
                        expect = Long.parseLong(m.group(1)) * Long.parseLong(m.group(2));
                        mulTotal++;
                        if (Long.parseLong(q.options.get(q.answerIndex)) != expect) { mulBad++; if (mulSample.isEmpty()) mulSample = q.text + " marked=" + q.options.get(q.answerIndex) + " expect=" + expect; }
                    } else if ((m = divPat.matcher(q.text)).matches()) {
                        expect = Long.parseLong(m.group(1)) / Long.parseLong(m.group(2));
                        if (Long.parseLong(q.options.get(q.answerIndex)) != expect) { otherBad++; if (otherSample.isEmpty()) otherSample = q.text; }
                    } else if ((m = addPat.matcher(q.text)).matches()) {
                        expect = Long.parseLong(m.group(1)) + Long.parseLong(m.group(2));
                        if (Long.parseLong(q.options.get(q.answerIndex)) != expect) { otherBad++; if (otherSample.isEmpty()) otherSample = q.text; }
                    } else if ((m = subPat.matcher(q.text)).matches()) {
                        expect = Long.parseLong(m.group(1)) - Long.parseLong(m.group(2));
                        if (Long.parseLong(q.options.get(q.answerIndex)) != expect) { otherBad++; if (otherSample.isEmpty()) otherSample = q.text; }
                    } else { otherBad++; if (otherSample.isEmpty()) otherSample = "unparsed: " + q.text; }
                }
            }
            check("T4.13a genMath 加减除/混合/方程：答案=重算值", otherBad == 0, "bad=" + otherBad + "; " + otherSample);
            check("T4.13b genMath 乘法：答案=a*b", mulBad == 0,
                    mulBad + "/" + mulTotal + " wrong; e.g. " + mulSample);
            check("T4.13c genMath 选项 4 个互异", dupOpt == 0, "dup=" + dupOpt);
            check("T4.13d genMath 无负数干扰项", negDistractor == 0, "negDistractor=" + negDistractor);
            System.out.println("INFO | T4.13e 五六年级负数答案出现 " + negAnswer + " 次（P3：答案可为负、干扰项恒非负，五六年级未学负数）");
        }

        // T4.14 CSV 导出：含逗号题库引号转义 + 列对齐
        {
            String out = qb.exportCsv("math_g9");
            String[] lines = out.split("\r\n");
            int misalign = 0;
            for (int i = 1; i < lines.length; i++) {
                if (lines[i].trim().isEmpty()) continue;
                // 数顶层列数（引号外逗号）
                int cols = 0; boolean inQ = false;
                for (char c : lines[i].toCharArray()) {
                    if (c == '"') inQ = !inQ;
                    else if (c == ',' && !inQ) cols++;
                }
                if (cols != 6) misalign++;
            }
            check("T4.14 Android exportCsv 含逗号库列对齐（引号转义）", misalign == 0, misalign + " 行错位");
        }

        // T4.15 CSV 导入：引号包裹字段/CRLF/BOM/表头
        {
            String csv = "\uFEFF题干,选项A,选项B,选项C,选项D,答案,大字\r\n"
                    + "\"含,逗号题干,x\",o1,o2,o3,o4,C,字\r\n"
                    + "普通题,a,b,c,d,A,\r\n";
            int n = qb.bankSize(qb.importCsv("quoted", csv));
            check("T4.15a 导入引号包裹含逗号题干", n == 2, "n=" + n);
            boolean found = false;
            for (int i = 0; i < 60 && !found; i++) {
                QuestionBank.Question q = qb.getQuestion("custom_quoted");
                if (q.text.contains("含,逗号题干,x")) {
                    found = q.options.get(q.answerIndex).equals("o3"); // C → 第三个选项
                }
            }
            check("T4.15b 引号字段还原+答案正确", found);
            // 空内容
            boolean threw = false;
            try { qb.importCsv("bad", "只有一列,两列"); } catch (Exception e) { threw = true; }
            check("T4.15c 非法内容抛异常", threw);
        }

        // T4.16 导出→导入 round-trip（含逗号库 math_g9）
        {
            String out = qb.exportCsv("math_g9");
            int n = qb.bankSize(qb.importCsv("rt9", out));
            int expect = jsonData.getJSONObject("banks").getJSONArray("math_g9").length();
            int intact = 0;
            for (int i = 0; i < 200; i++) {
                QuestionBank.Question q = qb.getQuestion("custom_rt9");
                String t = q.text;
                org.json.JSONArray arr = jsonData.getJSONObject("banks").getJSONArray("math_g9");
                for (int j = 0; j < arr.length(); j++) {
                    if (arr.getJSONObject(j).getString("q").equals(t)) { intact++; break; }
                }
            }
            Set<String> seenTexts = new HashSet<>();
            for (int i = 0; i < 500; i++) seenTexts.add(qb.getQuestion("custom_rt9").text);
            int distinctIntact = 0;
            for (String t : seenTexts) {
                org.json.JSONArray arr = jsonData.getJSONObject("banks").getJSONArray("math_g9");
                for (int j = 0; j < arr.length(); j++) {
                    if (arr.getJSONObject(j).getString("q").equals(t)) { distinctIntact++; break; }
                }
            }
            check("T4.16 Android 导出 math_g9→导入 round-trip", n == expect && distinctIntact == expect,
                    String.format("n=%d/%d 完整题干 %d/%d", n, expect, distinctIntact, expect));
        }

        // T4.17 自定义库持久化
        {
            qb.importCsv("persistA", "q1,a,b,c,d,A,");
            TestContext ctx2 = new TestContext();
            QuestionBank qb2 = new QuestionBank(ctx2);
            boolean ok = false;
            for (QuestionBank.BankItem b : qb2.getBankList()) {
                if (b.custom && b.id.equals("custom_persistA")) ok = true;
            }
            check("T4.17 自定义库持久化（新实例可见）", ok);
        }

        // T4.18 getLabel
        check("T4.18 label 查询", qb.getLabel("chinese_g5").contains("五年级") || !qb.getLabel("chinese_g5").equals("chinese_g5"),
                qb.getLabel("chinese_g5"));

        System.out.println("\n===== T4 Android JVM: " + p + " PASS / " + f + " FAIL =====");
        if (f > 0) { System.out.println("失败项:"); System.out.println(fails); System.exit(1); }
    }

    static void prefTests() {
        TestContext ctx = new TestContext();
        PrefManager pref = new PrefManager(ctx);

        // T4.1 默认值
        check("T4.1a 默认 PIN=1234", pref.getParentPin().equals("1234"));
        check("T4.1b 默认解锁题数=3", pref.getUnlockCount() == 3);
        check("T4.1c 默认观看时长=1800 秒", pref.getWatchLimitSeconds() == 1800);
        check("T4.1d 默认自启=开", pref.isAutoStart());
        check("T4.1e 默认未锁屏/未计时", !pref.isLocked() && !pref.isTimerActive());

        // T4.2 旧版分钟迁移
        {
            TestContext c2 = new TestContext();
            SharedPreferences.MemPrefs store = (SharedPreferences.MemPrefs) c2.getSharedPreferences("x", 0);
            store.edit().putInt("watch_limit_min", 15).apply();
            PrefManager p2 = new PrefManager(c2);
            check("T4.2 旧版分钟值迁移（15min→900s）", p2.getWatchLimitSeconds() == 900, "got=" + p2.getWatchLimitSeconds());
        }

        // T4.3 计时状态机
        {
            TestContext c3 = new TestContext();
            PrefManager p3 = new PrefManager(c3);
            p3.setLocked(true);
            p3.startTimer(30);
            check("T4.3a startTimer 置 active 并解除锁屏", p3.isTimerActive() && !p3.isLocked());
            check("T4.3b 剩余≈30s", Math.abs(p3.getRemainingMillis() - 30000) < 1500, p3.getRemainingMillis() + "ms");
            check("T4.3c 未到期", !p3.isTimerExpired());
            // 时间旅行：直接把 end 改到过去
            SharedPreferences.MemPrefs st = (SharedPreferences.MemPrefs) c3.getSharedPreferences("x", 0);
            st.edit().putLong("timer_end_time", System.currentTimeMillis() - 1).apply();
            check("T4.3d 到期判定（end=now-1）", p3.isTimerExpired());
            st.edit().putLong("timer_end_time", 0).apply();
            check("T4.3e remaining 钳位 ≥0", p3.getRemainingMillis() == 0);
            p3.stopTimer();
            check("T4.3f stopTimer", !p3.isTimerActive() && p3.getTimerEndTime() == 0 && !p3.isTimerExpired());
        }

        // T4.4 PIN 防暴力状态机
        {
            TestContext c4 = new TestContext();
            PrefManager p4 = new PrefManager(c4);
            for (int i = 0; i < 4; i++) p4.recordPinFailure();
            check("T4.4a 连错 4 次未锁定", !p4.isPinLocked());
            p4.recordPinFailure(); // 第 5 次
            check("T4.4b 第 5 次触发 30s 锁定", p4.isPinLocked());
            long remain = p4.getPinLockRemainingMillis();
            check("T4.4c 锁定剩余 ≈30s", remain > 28000 && remain <= 30000, remain + "ms");
            // 失败计数在锁定时已清零
            SharedPreferences.MemPrefs st = (SharedPreferences.MemPrefs) c4.getSharedPreferences("x", 0);
            check("T4.4d 锁定后失败计数归零", st.getInt("pin_fail_count", -1) == 0);
            // 时间旅行到锁定期满
            st.edit().putLong("pin_lock_until", System.currentTimeMillis() - 1).apply();
            check("T4.4e 锁定期满自动解锁", !p4.isPinLocked());
            // 再错 4 次不锁，第 5 次再锁
            for (int i = 0; i < 4; i++) p4.recordPinFailure();
            check("T4.4f 第二轮 4 次未锁", !p4.isPinLocked());
            p4.recordPinFailure();
            check("T4.4g 第二轮第 5 次再锁", p4.isPinLocked());
            p4.resetPinFailures();
            check("T4.4h reset 清除锁定", !p4.isPinLocked());
        }

        // T4.5 HOME alias 仅电视生效
        {
            TestContext phone = new TestContext(); // tvDevice=false
            PrefManager pp = new PrefManager(phone);
            pp.setHomeAliasEnabled(phone, true);
            check("T4.5a 手机设备不启用 HOME alias", phone.getPackageManager().lastAliasState.equals("none"));
            TestContext tv = new TestContext();
            tv.tvDevice = true;
            tv.getPackageManager().leanback = true;
            PrefManager tp = new PrefManager(tv);
            tp.setHomeAliasEnabled(tv, true);
            check("T4.5b 电视启用 HOME alias", tv.getPackageManager().lastAliasState.contains("ENABLED"));
            tp.setHomeAliasEnabled(tv, false);
            check("T4.5c 解除 HOME alias", tv.getPackageManager().lastAliasState.contains("DISABLED"));
        }

        // T4.6 设置写入
        {
            TestContext c6 = new TestContext();
            PrefManager p6 = new PrefManager(c6);
            p6.setParentPin("9999"); p6.setUnlockCount(10); p6.setWatchLimitSeconds(30); p6.setAutoStart(false); p6.setBankId("math_g7");
            check("T4.6 设置写入回读", p6.getParentPin().equals("9999") && p6.getUnlockCount() == 10
                    && p6.getWatchLimitSeconds() == 30 && !p6.isAutoStart() && p6.getBankId().equals("math_g7"));
        }
    }

    /** 提供 prefs 存储共享入口 */
    static class TestContext extends android.content.Context {
    }
}
