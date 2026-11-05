package com.kidslock.app;

import android.content.Context;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

/**
 * 人教版语数英题库引擎（按年级：1-12 年级 × 3 学科 = 36 内置库）。
 * - 内置题来自 res/raw/questions.json（三平台共享）
 * - 小学/初中数学按年级程序生成，可无限出题
 * - 支持自定义题库（CSV 导入，filesDir/custom_banks.json 持久化）
 * - CSV 导出：题干,选项A..D,答案(A-D),大字
 */
public class QuestionBank {

    private static final String TAG = "QuestionBank";
    private static final String CUSTOM_FILE = "custom_banks.json";
    public static final String CUSTOM_PREFIX = "custom_";

    public static class Question {
        public final String text;
        public final String bigChar;        // 字音题大字（其他为 null）
        public final List<String> options;  // 已打乱
        public final int answerIndex;

        Question(String text, String bigChar, List<String> options, int answerIndex) {
            this.text = text;
            this.bigChar = bigChar;
            this.options = options;
            this.answerIndex = answerIndex;
        }
    }

    /** 题库条目（id + 显示名） */
    public static class BankItem {
        public final String id;
        public final String label;
        public final boolean custom;

        public BankItem(String id, String label, boolean custom) {
            this.id = id;
            this.label = label;
            this.custom = custom;
        }
    }

    private final Context context;
    private final Random random = new Random();
    private final JSONObject banks = new JSONObject();
    private final Map<String, String> labels = new HashMap<>();
    // 自定义库：id -> 题目数组（JSON 格式同内置）
    private final Map<String, List<JSONObject>> customBanks = new HashMap<>();
    private final Map<String, String> customLabels = new HashMap<>();

    public QuestionBank(Context context) {
        this.context = context;
        try (InputStream in = context.getResources().openRawResource(R.raw.questions)) {
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) bos.write(buf, 0, n);
            JSONObject root = new JSONObject(bos.toString("UTF-8"));
            JSONObject b = root.getJSONObject("banks");
            java.util.Iterator<String> keys = b.keys();
            while (keys.hasNext()) {
                String k = keys.next();
                banks.put(k, b.get(k));
            }
            JSONObject l = root.getJSONObject("labels");
            java.util.Iterator<String> lk = l.keys();
            while (lk.hasNext()) {
                String k = lk.next();
                labels.put(k, l.getString(k));
            }
        } catch (Exception e) {
            Log.e(TAG, "load questions.json failed", e);
        }
        loadCustomBanks();
    }

    // ==================== 题库清单 ====================

    /** 全部可选题库：内置 36（语/数/英 × 12 年级）+ 自定义库 */
    public List<BankItem> getBankList() {
        List<BankItem> list = new ArrayList<>();
        String[] subjects = {"chinese", "math", "english"};
        String[] subjectNames = {"语文", "数学", "英语"};
        String[] gradeNames = {"一年级", "二年级", "三年级", "四年级", "五年级", "六年级",
                "初一", "初二", "初三", "高一", "高二", "高三"};
        for (int s = 0; s < 3; s++) {
            for (int g = 1; g <= 12; g++) {
                String id = subjects[s] + "_g" + g;
                list.add(new BankItem(id, subjectNames[s] + "·" + gradeNames[g - 1], false));
            }
        }
        for (Map.Entry<String, String> e : customLabels.entrySet()) {
            list.add(new BankItem(e.getKey(), e.getValue(), true));
        }
        return list;
    }

    public String getLabel(String bankId) {
        bankId = resolveBankId(bankId);
        if (customLabels.containsKey(bankId)) return customLabels.get(bankId);
        String v = labels.get(bankId);
        return v != null ? v : bankId;
    }

    /** 兼容旧版三级库 id：primary→g5、junior→g7、senior→g10；无效 id 回退 chinese_g1 */
    public String resolveBankId(String bankId) {
        if (bankId != null) {
            if (bankId.startsWith(CUSTOM_PREFIX) && customBanks.containsKey(bankId)) return bankId;
            if (banks.has(bankId)) return bankId;
            if (bankId.endsWith("_primary")) return bankId.replace("_primary", "_g5");
            if (bankId.endsWith("_junior")) return bankId.replace("_junior", "_g7");
            if (bankId.endsWith("_senior")) return bankId.replace("_senior", "_g10");
        }
        return "chinese_g1";
    }

    // ==================== 出题 ====================

    public Question getQuestion(String bankId) {
        try {
            bankId = resolveBankId(bankId);
            if (bankId.startsWith(CUSTOM_PREFIX)) {
                List<JSONObject> arr = customBanks.get(bankId);
                if (arr != null && !arr.isEmpty()) {
                    JSONObject item = arr.get(random.nextInt(arr.size()));
                    return shuffle(item.getString("q"),
                            item.isNull("char") ? null : item.getString("char"),
                            item.getJSONArray("opts"), item.getInt("ans"));
                }
            }
            // 数学按年级程序生成（30% 概率，避免重复感）
            int grade = parseGrade(bankId);
            if (bankId.startsWith("math") && grade >= 1 && grade <= 9 && random.nextInt(100) < 30) {
                Question gq = genMath(grade);
                if (gq != null) return gq;
            }
            JSONArray arr = banks.getJSONArray(bankId);
            if (arr.length() == 0) throw new IllegalStateException("empty bank " + bankId);
            JSONObject item = arr.getJSONObject(random.nextInt(arr.length()));
            return shuffle(item.getString("q"),
                    item.isNull("char") ? null : item.getString("char"),
                    item.getJSONArray("opts"), item.getInt("ans"));
        } catch (Exception e) {
            Log.e(TAG, "getQuestion failed for " + bankId, e);
            return new Question("出题出错，请重试", null,
                    java.util.Arrays.asList("1", "2", "3", "4"), 0);
        }
    }

    private int parseGrade(String bankId) {
        try {
            int i = bankId.indexOf("_g");
            if (i >= 0) return Integer.parseInt(bankId.substring(i + 2));
        } catch (Exception ignore) {
        }
        return -1;
    }

    private Question shuffle(String text, String bigChar, JSONArray optsArr, int ansIdx) {
        try {
            List<String> opts = new ArrayList<>();
            String correct = optsArr.getString(ansIdx);
            Set<String> seen = new HashSet<>();
            for (int i = 0; i < optsArr.length() && opts.size() < 4; i++) {
                String o = optsArr.getString(i).trim();
                if (!o.isEmpty() && seen.add(o)) opts.add(o);
            }
            while (opts.size() < 4) opts.add("—");
            Collections.shuffle(opts, random);
            int idx = opts.indexOf(correct);
            return new Question(text, bigChar, opts, Math.max(0, idx));
        } catch (Exception e) {
            return new Question(text, bigChar, java.util.Arrays.asList("1", "2", "3", "4"), 0);
        }
    }

    // ==================== 数学按年级生成 ====================

    private Question genMath(int grade) {
        try {
            if (grade <= 2) {
                int op = random.nextInt(2);
                int a, b, r;
                if (op == 0) {
                    a = ri(grade == 1 ? 1 : 11, grade == 1 ? 10 : 89);
                    b = ri(1, grade == 1 ? 10 : 89);
                    r = a + b;
                    return buildNumeric(String.format("%d + %d = ?", a, b), r);
                } else {
                    a = ri(grade == 1 ? 2 : 30, grade == 1 ? 10 : 99);
                    b = ri(1, a - 1);
                    r = a - b;
                    return buildNumeric(String.format("%d - %d = ?", a, b), r);
                }
            } else if (grade <= 4) {
                int b = ri(3, 9), r = ri(3, grade <= 3 ? 9 : 40), a = b * r;
                if (random.nextBoolean()) {
                    // 乘法标答是 a×b 本身；除法分支 a÷b = r
                    return buildNumeric(String.format("%d × %d = ?", a, b), a * b);
                }
                return buildNumeric(String.format("%d ÷ %d = ?", a, b), r);
            } else if (grade <= 6) {
                int a = ri(11, 60), b = ri(2, 20);
                // 五六年级未学负数：c 不超过 a+b-1，保证结果 ≥ 1
                int c = ri(5, Math.min(40, a + b - 1));
                int r = a + b - c;
                return buildNumeric(String.format("%d + %d - %d = ?", a, b, c), r);
            } else {
                int a = ri(2, 9), x = ri(1, 15), b = ri(1, 40);
                int c = a * x + b;
                return buildNumeric(String.format("解方程：%dx + %d = %d，x = ?", a, b, c), x);
            }
        } catch (Exception e) {
            return null;
        }
    }

    private Question buildNumeric(String text, int r) {
        Set<Integer> set = new HashSet<>();
        set.add(r);
        while (set.size() < 4) {
            int d = ri(1, 9) * (random.nextInt(8) == 0 ? 10 : 1);
            int v = r + (random.nextBoolean() ? d : -d);
            if (v >= 0) set.add(v);
        }
        List<Integer> vals = new ArrayList<>(set);
        Collections.shuffle(vals, random);
        List<String> opts = new ArrayList<>();
        for (int v : vals) opts.add(String.valueOf(v));
        return new Question(text, null, opts, opts.indexOf(String.valueOf(r)));
    }

    private int ri(int min, int max) {
        return min + random.nextInt(Math.max(1, max - min + 1));
    }

    // ==================== CSV 导入导出 ====================

    private static final String CSV_HEAD = "题干,选项A,选项B,选项C,选项D,答案,大字";
    private static final String[] LETTERS = {"A", "B", "C", "D"};

    /** 导出某题库为 CSV 字符串 */
    public String exportCsv(String bankId) {
        StringBuilder sb = new StringBuilder();
        sb.append(CSV_HEAD).append("\r\n");
        List<JSONObject> items = new ArrayList<>();
        try {
            if (bankId.startsWith(CUSTOM_PREFIX)) {
                List<JSONObject> arr = customBanks.get(bankId);
                if (arr != null) items.addAll(arr);
            } else {
                JSONArray arr = banks.getJSONArray(bankId);
                for (int i = 0; i < arr.length(); i++) items.add(arr.getJSONObject(i));
            }
        } catch (Exception e) {
            Log.e(TAG, "exportCsv collect failed", e);
        }
        for (JSONObject it : items) {
            try {
                String[] opts = new String[4];
                JSONArray oa = it.getJSONArray("opts");
                for (int i = 0; i < 4; i++) opts[i] = oa.getString(i).replace(",", "，");
                String ans = LETTERS[it.getInt("ans")];
                String big = it.isNull("char") ? "" : it.getString("char");
                sb.append(csvCell(it.getString("q"))).append(",")
                        .append(csvCell(opts[0])).append(",")
                        .append(csvCell(opts[1])).append(",")
                        .append(csvCell(opts[2])).append(",")
                        .append(csvCell(opts[3])).append(",")
                        .append(ans).append(",")
                        .append(big).append("\r\n");
            } catch (Exception ignore) {
            }
        }
        return sb.toString();
    }

    private String csvCell(String s) {
        if (s.contains(",") || s.contains("\"") || s.contains("\n")) {
            return "\"" + s.replace("\"", "\"\"") + "\"";
        }
        return s;
    }

    /**
     * 从 CSV 文本导入为自定义题库。
     *
     * @param name     显示名（通常取文件名去扩展名）
     * @param csvText  CSV 内容（UTF-8）
     * @return 实际保存的自定义库 id（文件名已净化，调用方必须用该 id 选中题库）
     * @throws Exception 格式错误
     */
    public String importCsv(String name, String csvText) throws Exception {
        List<JSONObject> items = new ArrayList<>();
        List<String[]> rows = parseCsv(csvText);
        int start = 0;
        if (!rows.isEmpty()) {
            String h0 = rows.get(0).length > 0 ? rows.get(0)[0].trim() : "";
            if (h0.contains("题干")) start = 1; // 跳过表头
        }
        for (int i = start; i < rows.size(); i++) {
            String[] c = rows.get(i);
            if (c.length < 6) continue;
            String q = c[0].trim();
            if (q.isEmpty()) continue;
            JSONArray opts = new JSONArray();
            for (int k = 1; k <= 4; k++) opts.put(c[k].trim());
            String ansLetter = c[5].trim().toUpperCase();
            int ans = "ABCD".indexOf(ansLetter);
            if (ans < 0) ans = 0;
            JSONObject item = new JSONObject();
            item.put("q", q);
            item.put("opts", opts);
            item.put("ans", ans);
            item.put("char", c.length > 6 && !c[6].trim().isEmpty() ? c[6].trim() : JSONObject.NULL);
            items.add(item);
        }
        if (items.isEmpty()) throw new Exception("没有解析到有效题目（需≥4列选项+答案列）");

        String safeName = name.replaceAll("[\\\\/:*?\"<>|]", "_");
        String id = CUSTOM_PREFIX + safeName;
        customBanks.put(id, items);
        customLabels.put(id, "自定义·" + safeName);
        saveCustomBanks();
        return id;
    }

    /** 某题库的题目数（内置库或自定义库；导入成功的题数用它取） */
    public int bankSize(String bankId) {
        try {
            String id = resolveBankId(bankId);
            if (id.startsWith(CUSTOM_PREFIX)) {
                List<JSONObject> arr = customBanks.get(id);
                return arr == null ? 0 : arr.size();
            }
            return banks.getJSONArray(id).length();
        } catch (Exception e) {
            return 0;
        }
    }

    /** 极简 CSV 解析：支持双引号包裹与转义、\r\n 换行 */
    private List<String[]> parseCsv(String text) {
        List<String[]> rows = new ArrayList<>();
        List<String> cur = new ArrayList<>();
        StringBuilder cell = new StringBuilder();
        boolean inQuote = false;
        String s = text.replace("\uFEFF", "");
        for (int i = 0; i < s.length(); i++) {
            char ch = s.charAt(i);
            if (inQuote) {
                if (ch == '"') {
                    if (i + 1 < s.length() && s.charAt(i + 1) == '"') {
                        cell.append('"');
                        i++;
                    } else {
                        inQuote = false;
                    }
                } else cell.append(ch);
            } else if (ch == '"') {
                inQuote = true;
            } else if (ch == ',') {
                cur.add(cell.toString());
                cell.setLength(0);
            } else if (ch == '\n') {
                cur.add(cell.toString());
                rows.add(cur.toArray(new String[0]));
                cur = new ArrayList<>();
                cell.setLength(0);
            } else if (ch != '\r') {
                cell.append(ch);
            }
        }
        if (cell.length() > 0 || !cur.isEmpty()) {
            cur.add(cell.toString());
            rows.add(cur.toArray(new String[0]));
        }
        return rows;
    }

    // ==================== 自定义库持久化 ====================

    private void loadCustomBanks() {
        try {
            File f = new File(context.getFilesDir(), CUSTOM_FILE);
            if (!f.exists()) return;
            StringBuilder sb = new StringBuilder();
            try (BufferedReader br = new BufferedReader(new InputStreamReader(
                    new FileInputStream(f), StandardCharsets.UTF_8))) {
                String line;
                while ((line = br.readLine()) != null) sb.append(line);
            }
            JSONObject root = new JSONObject(sb.toString());
            java.util.Iterator<String> keys = root.keys();
            while (keys.hasNext()) {
                String id = keys.next();
                JSONObject o = root.getJSONObject(id);
                List<JSONObject> items = new ArrayList<>();
                JSONArray arr = o.getJSONArray("items");
                for (int i = 0; i < arr.length(); i++) items.add(arr.getJSONObject(i));
                customBanks.put(id, items);
                customLabels.put(id, o.getString("label"));
            }
        } catch (Exception e) {
            Log.e(TAG, "loadCustomBanks failed", e);
        }
    }

    private void saveCustomBanks() {
        try {
            JSONObject root = new JSONObject();
            for (Map.Entry<String, List<JSONObject>> e : customBanks.entrySet()) {
                JSONObject o = new JSONObject();
                o.put("label", customLabels.get(e.getKey()));
                JSONArray arr = new JSONArray();
                for (JSONObject it : e.getValue()) arr.put(it);
                o.put("items", arr);
                root.put(e.getKey(), o);
            }
            try (OutputStreamWriter w = new OutputStreamWriter(
                    context.openFileOutput(CUSTOM_FILE, Context.MODE_PRIVATE), StandardCharsets.UTF_8)) {
                w.write(root.toString());
            }
        } catch (Exception e) {
            Log.e(TAG, "saveCustomBanks failed", e);
        }
    }
}
