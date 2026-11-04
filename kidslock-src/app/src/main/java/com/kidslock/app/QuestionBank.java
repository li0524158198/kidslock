package com.kidslock.app;

import android.content.Context;
import android.util.Log;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Random;
import java.util.Set;

/**
 * 人教版语数英题库引擎（小学/初中/高中 × 3 学科）。
 * 内置题来自 assets questions.json（三平台共享同一份数据）；
 * 小学/初中数学额外内置程序生成器，可无限出题。
 */
public class QuestionBank {

    private static final String TAG = "QuestionBank";

    /** 一道题 */
    public static class Question {
        public final String text;      // 题干
        public final String bigChar;   // 字音题的大字（非字音题为 null）
        public final List<String> options; // 已打乱的 4 个选项
        public final int answerIndex;      // 打乱后正确答案下标

        Question(String text, String bigChar, List<String> options, int answerIndex) {
            this.text = text;
            this.bigChar = bigChar;
            this.options = options;
            this.answerIndex = answerIndex;
        }
    }

    // labels 由 JSON 读取；这里维护固定顺序供 UI 使用
    public static final String[] BANK_IDS = {
            "chinese_primary", "math_primary", "english_primary",
            "chinese_junior", "math_junior", "english_junior",
            "chinese_senior", "math_senior", "english_senior",
    };

    private final JSONObject banks;
    private final JSONObject labels;
    private final Random random = new Random();

    public QuestionBank(Context context) {
        JSONObject b = null, l = null;
        try (InputStream in = context.getResources().openRawResource(R.raw.questions)) {
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) bos.write(buf, 0, n);
            JSONObject root = new JSONObject(bos.toString("UTF-8"));
            b = root.getJSONObject("banks");
            l = root.getJSONObject("labels");
        } catch (Exception e) {
            Log.e(TAG, "Failed to load questions.json", e);
        }
        banks = b;
        labels = l;
    }

    /** 题库显示名（如「语文·小学」） */
    public String getLabel(String bankId) {
        try {
            return labels.getString(bankId);
        } catch (Exception e) {
            return bankId;
        }
    }

    /** 取一道题（随机 + 选项打乱；小学/初中数学 50% 概率动态生成） */
    public Question getQuestion(String bankId) {
        if (banks == null) {
            return new Question("题库加载失败", null, java.util.Arrays.asList("1", "2", "3", "4"), 0);
        }
        if ("math_primary".equals(bankId) && random.nextBoolean()) {
            return genPrimaryMath();
        }
        if ("math_junior".equals(bankId) && random.nextBoolean()) {
            return genJuniorEquation();
        }
        try {
            org.json.JSONArray arr = banks.getJSONArray(bankId);
            if (arr.length() == 0) throw new IllegalStateException("empty bank");
            org.json.JSONObject item = arr.getJSONObject(random.nextInt(arr.length()));
            return shuffle(item.getString("q"),
                    item.isNull("char") ? null : item.getString("char"),
                    item.getJSONArray("opts"),
                    item.getInt("ans"));
        } catch (Exception e) {
            Log.e(TAG, "getQuestion failed for " + bankId, e);
            return new Question("出题出错，请重试", null, java.util.Arrays.asList("1", "2", "3", "4"), 0);
        }
    }

    /** 打乱选项并重定位正确答案 */
    private Question shuffle(String text, String bigChar, org.json.JSONArray optsArr, int ansIdx) {
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
            return new Question(text, bigChar, opts, opts.indexOf(correct));
        } catch (Exception e) {
            return new Question(text, bigChar, java.util.Arrays.asList("1", "2", "3", "4"), 0);
        }
    }

    /** 小学数学：四则运算无限生成 */
    private Question genPrimaryMath() {
        int op = random.nextInt(4);
        int a, b, r;
        String sym;
        switch (op) {
            case 0: a = ri(12, 89); b = ri(12, 89); r = a + b; sym = "+"; break;
            case 1: a = ri(30, 99); b = ri(11, a - 1); r = a - b; sym = "-"; break;
            case 2: a = ri(3, 12); b = ri(3, 12); r = a * b; sym = "×"; break;
            default: b = ri(3, 9); r = ri(3, 12); a = b * r; sym = "÷"; break;
        }
        return buildNumeric(String.format("%d %s %d = ?", a, sym, b), r);
    }

    /** 初中数学：一元一次方程 ax + b = c 无限生成 */
    private Question genJuniorEquation() {
        int a = ri(2, 9), x = ri(1, 12), b = ri(1, 30);
        int c = a * x + b;
        return buildNumeric(String.format("解方程：%dx + %d = %d，x = ?", a, b, c), x);
    }

    /** 数字题：正确答案 + 3 个邻近干扰项 */
    private Question buildNumeric(String text, int r) {
        Set<Integer> set = new HashSet<>();
        set.add(r);
        while (set.size() < 4) {
            int d = ri(1, 9) * (random.nextInt(10) == 0 ? 10 : 1);
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
}
