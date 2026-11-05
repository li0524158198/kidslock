package com.kidslock.app;

import android.content.DialogInterface;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * 设置主界面。
 * 家长可以在这里配置：开机自启、观看时长、解锁题数、家长PIN码、答题题库（人教版按年级/自定义 CSV）。
 * 还可以开始/停止计时、立即锁屏、查看剩余时间。
 */
public class MainActivity extends AppCompatActivity {

    private static final int REQ_IMPORT_CSV = 41;
    private static final int REQ_EXPORT_CSV = 42;

    private PrefManager pref;
    private final Handler handler = new Handler(Looper.getMainLooper());

    private TextView tvStatus;
    private TextView tvRemaining;
    private Button btnAutoStart;
    private TextView tvWatchTime;
    private TextView tvUnlockCount;

    private Button[] subjectButtons;
    private Button[] gradeButtons;
    private LinearLayout customBankRow;
    private Button btnImportCsv;
    private Button btnExportCsv;
    private String currentSubject = "chinese";
    private String exportBankId; // 导出挂起的库 id

    private QuestionBank questionBank;

    private final Runnable updateRunnable = new Runnable() {
        @Override
        public void run() {
            updateStatus();
            handler.postDelayed(this, 1000);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        pref = new PrefManager(this);

        // 如果当前处于锁屏状态，禁止进入设置页（防止从桌面图标绕过锁屏解锁）
        if (pref.isLocked()) {
            Intent lockIntent = new Intent(this, LockScreenActivity.class);
            lockIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            startActivity(lockIntent);
            finish();
            return;
        }

        // 计时自愈：服务曾被系统/强杀停止时，重新拉起 LockService 继续倒计时（已到期则直接锁屏）
        if (pref.isTimerActive()) {
            startLockService();
        }

        setContentView(R.layout.activity_main);

        initViews();
        setupListeners();
        updateStatus();
    }

    @Override
    protected void onResume() {
        super.onResume();
        handler.post(updateRunnable);
    }

    @Override
    protected void onPause() {
        super.onPause();
        handler.removeCallbacks(updateRunnable);
    }

    private void initViews() {
        tvStatus = findViewById(R.id.tvStatus);
        tvRemaining = findViewById(R.id.tvRemaining);
        btnAutoStart = findViewById(R.id.btnAutoStart);
        tvWatchTime = findViewById(R.id.tvWatchTime);
        tvUnlockCount = findViewById(R.id.tvUnlockCount);
        try {
            String vn = getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
            ((TextView) findViewById(R.id.tvVersion)).setText("v" + vn);
        } catch (Exception ignore) {
        }

        questionBank = new QuestionBank(this);

        // 学科按钮（语文/数学/英语）：点击立即切换到该学科（保留当前年级）
        int[] subjectIds = {R.id.subject0, R.id.subject1, R.id.subject2};
        String[] subjects = {"chinese", "math", "english"};
        subjectButtons = new Button[3];
        for (int i = 0; i < 3; i++) {
            Button b = findViewById(subjectIds[i]);
            final String s = subjects[i];
            b.setOnClickListener(v -> {
                currentSubject = s;
                int grade = savedGrade();
                pref.setBankId(s + "_g" + grade);
                updateStatus();
                refreshBankSelection();
                toast("题库：" + questionBank.getLabel(s + "_g" + grade));
            });
            subjectButtons[i] = b;
        }

        // 年级按钮（12 个）
        int[] gradeIds = {R.id.grade0, R.id.grade1, R.id.grade2, R.id.grade3, R.id.grade4, R.id.grade5,
                R.id.grade6, R.id.grade7, R.id.grade8, R.id.grade9, R.id.grade10, R.id.grade11};
        gradeButtons = new Button[12];
        for (int g = 0; g < 12; g++) {
            Button b = findViewById(gradeIds[g]);
            final int grade = g + 1;
            b.setOnClickListener(v -> {
                pref.setBankId(currentSubject + "_g" + grade);
                updateStatus();
                refreshBankSelection();
                toast("题库：" + questionBank.getLabel(currentSubject + "_g" + grade));
            });
            gradeButtons[g] = b;
        }

        // 自定义库列表容器
        customBankRow = findViewById(R.id.customBankRow);

        // CSV 导入导出
        btnImportCsv = findViewById(R.id.csvBtn0);
        btnExportCsv = findViewById(R.id.csvBtn1);
        btnImportCsv.setOnClickListener(v -> startImportCsv());
        btnExportCsv.setOnClickListener(v -> startExportCsv());

        syncSubjectFromBank();
        refreshBankSelection();
        refreshCustomBankList();
    }

    /** 从已保存 bankId 反推当前学科（内置库） */
    private void syncSubjectFromBank() {
        String id = questionBank.resolveBankId(pref.getBankId());
        if (id.startsWith("math")) currentSubject = "math";
        else if (id.startsWith("english")) currentSubject = "english";
        else if (id.startsWith("chinese")) currentSubject = "chinese";
    }

    /** 从已保存 bankId 解析年级（1..12），自定义库或解析失败回退 1 */
    private int savedGrade() {
        String id = questionBank.resolveBankId(pref.getBankId());
        try {
            int g = Integer.parseInt(id.substring(id.indexOf("_g") + 2));
            if (g >= 1 && g <= 12) return g;
        } catch (Exception ignore) {
        }
        return 1;
    }

    private void refreshBankSelection() {
        String current = questionBank.resolveBankId(pref.getBankId());
        // 学科高亮
        for (int i = 0; i < 3; i++) {
            boolean sel = current.startsWith(subjectIdOf(i));
            subjectButtons[i].setBackgroundResource(sel ? R.drawable.btn_bank_selected : R.drawable.btn_settings_bg);
            subjectButtons[i].setTextColor(sel ? 0xFF2A9D5C : 0xFFE0E1DD);
        }
        // 年级高亮（仅当当前库属于该学科）
        boolean bankInSubject = current.startsWith(subjectIdOf(currentSubject));
        int curGrade = -1;
        try {
            curGrade = Integer.parseInt(current.substring(current.indexOf("_g") + 2));
        } catch (Exception ignore) {
        }
        for (int g = 0; g < 12; g++) {
            boolean sel = bankInSubject && curGrade == g + 1;
            gradeButtons[g].setBackgroundResource(sel ? R.drawable.btn_bank_selected : R.drawable.btn_settings_bg);
            gradeButtons[g].setTextColor(sel ? 0xFF2A9D5C : 0xFFE0E1DD);
        }
        refreshCustomBankList();
    }

    private String subjectIdOf(int index) {
        return new String[]{"chinese", "math", "english"}[index];
    }

    private String subjectIdOf(String subject) {
        return subject;
    }

    /** 刷新自定义题库横向按钮列表 */
    private void refreshCustomBankList() {
        if (customBankRow == null) return;
        customBankRow.removeAllViews();
        List<QuestionBank.BankItem> items = questionBank.getBankList();
        String current = questionBank.resolveBankId(pref.getBankId());
        for (QuestionBank.BankItem item : items) {
            if (!item.custom) continue;
            Button b = new Button(this);
            b.setText(item.label);
            b.setAllCaps(false);
            b.setTextSize(14);
            b.setBackgroundResource(item.id.equals(current)
                    ? R.drawable.btn_bank_selected : R.drawable.btn_settings_bg);
            b.setTextColor(item.id.equals(current) ? 0xFF2A9D5C : 0xFFE0E1DD);
            b.setPadding(24, 8, 24, 8);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
            lp.setMargins(8, 4, 8, 4);
            b.setLayoutParams(lp);
            b.setOnClickListener(v -> {
                pref.setBankId(item.id);
                updateStatus();
                toast("已切换：" + item.label);
            });
            customBankRow.addView(b);
        }
    }

    // ==================== CSV 导入导出（SAF，无需存储权限） ====================

    private void startImportCsv() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        try {
            startActivityForResult(intent, REQ_IMPORT_CSV);
        } catch (Exception e) {
            toast("无法打开文件选择器");
        }
    }

    private void startExportCsv() {
        exportBankId = questionBank.resolveBankId(pref.getBankId());
        String suggest = exportBankId + ".csv";
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("text/csv");
        intent.putExtra(Intent.EXTRA_TITLE, suggest);
        try {
            startActivityForResult(intent, REQ_EXPORT_CSV);
        } catch (Exception e) {
            toast("无法打开文件选择器");
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK || data == null || data.getData() == null) return;
        Uri uri = data.getData();
        if (requestCode == REQ_IMPORT_CSV) {
            try (InputStream in = getContentResolver().openInputStream(uri);
                 BufferedReader br = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = br.readLine()) != null) sb.append(line).append("\n");
                String name = queryDisplayName(uri);
                String bankId = questionBank.importCsv(name, sb.toString());
                pref.setBankId(bankId);
                refreshBankSelection();
                refreshCustomBankList();
                toast("导入成功：" + questionBank.bankSize(bankId) + " 题");
            } catch (Exception e) {
                toast("导入失败：" + e.getMessage());
            }
        } else if (requestCode == REQ_EXPORT_CSV) {
            try (OutputStream out = getContentResolver().openOutputStream(uri)) {
                String csv = questionBank.exportCsv(exportBankId);
                out.write(csv.getBytes(StandardCharsets.UTF_8));
                toast("已导出 " + questionBank.getLabel(exportBankId));
            } catch (Exception e) {
                toast("导出失败：" + e.getMessage());
            }
        }
    }

    private String queryDisplayName(Uri uri) {
        String name = "custom";
        try (android.database.Cursor c = getContentResolver().query(uri, null, null, null, null)) {
            if (c != null && c.moveToFirst()) {
                int idx = c.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME);
                if (idx >= 0) name = c.getString(idx);
            }
        } catch (Exception ignore) {
        }
        if (name.toLowerCase().endsWith(".csv")) name = name.substring(0, name.length() - 4);
        return name;
    }

    // ==================== 原有设置逻辑 ====================

    private void setupListeners() {
        // 自动继续（开机自动开始计时 + 答题解锁后自动开始下一轮）
        btnAutoStart.setOnClickListener(v -> {
            boolean newVal = !pref.isAutoStart();
            pref.setAutoStart(newVal);
            updateStatus();
            toast(newVal ? "已开启自动继续" : "已关闭自动继续");
        });

        // 观看时长预设（单位：秒，含 30 秒测试档）
        int[] timeButtons = {R.id.btnTime30s, R.id.btnTime15, R.id.btnTime30,
                R.id.btnTime45, R.id.btnTime60, R.id.btnTime90, R.id.btnTime120};
        int[] timeValues = {30, 900, 1800, 2700, 3600, 5400, 7200};
        for (int i = 0; i < timeButtons.length; i++) {
            final int seconds = timeValues[i];
            findViewById(timeButtons[i]).setOnClickListener(v -> {
                pref.setWatchLimitSeconds(seconds);
                updateStatus();
                toast("观看时长设为 " + formatDuration(seconds));
            });
        }

        // 解锁题数预设
        int[] countButtons = {R.id.btnUnlock3, R.id.btnUnlock5, R.id.btnUnlock10};
        int[] countValues = {3, 5, 10};
        for (int i = 0; i < countButtons.length; i++) {
            final int count = countValues[i];
            findViewById(countButtons[i]).setOnClickListener(v -> {
                pref.setUnlockCount(count);
                updateStatus();
                toast("解锁题数设为 " + count + " 题");
            });
        }

        // 设置PIN码
        findViewById(R.id.btnSetPin).setOnClickListener(v -> showPinDialog());

        // 开始计时
        findViewById(R.id.btnStartTimer).setOnClickListener(v -> {
            int seconds = pref.getWatchLimitSeconds();
            pref.startTimer(seconds);
            startLockService();
            toast("计时开始：" + formatDuration(seconds) + "后锁屏");
            updateStatus();
        });

        // 停止计时
        findViewById(R.id.btnStopTimer).setOnClickListener(v -> {
            pref.stopTimer();
            stopService(new Intent(this, LockService.class));
            toast("计时已停止");
            updateStatus();
        });

        // 立即锁屏
        findViewById(R.id.btnLockNow).setOnClickListener(v -> {
            pref.setLocked(true);
            pref.setHomeAliasEnabled(this, true);
            pref.stopTimer();
            startLockService();
            Intent lockIntent = new Intent(this, LockScreenActivity.class);
            lockIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            startActivity(lockIntent);
        });

        // 立即解锁（如果在锁屏状态，从设置页解锁）
        findViewById(R.id.btnUnlock).setOnClickListener(v -> {
            pref.setLocked(false);
            pref.setHomeAliasEnabled(this, false);
            toast("已解锁");
            updateStatus();
        });
    }

    private void showPinDialog() {
        android.app.AlertDialog.Builder builder = new android.app.AlertDialog.Builder(this);
        builder.setTitle("设置家长PIN码（4位数字）");

        final EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_NUMBER);
        input.setRawInputType(android.text.InputType.TYPE_CLASS_NUMBER);
        input.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(4)});
        builder.setView(input);

        builder.setPositiveButton("确定", (dialog, which) -> {
            String pin = input.getText().toString().trim();
            if (pin.length() == 4) {
                pref.setParentPin(pin);
                toast("PIN码已设置");
            } else {
                toast("PIN码必须是4位数字");
            }
        });
        builder.setNegativeButton("取消", null);
        builder.show();
    }

    private void startLockService() {
        Intent serviceIntent = new Intent(this, LockService.class);
        serviceIntent.putExtra("action", "start_timer");
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }
    }

    /** 时长格式化：<60 秒显示"X 秒"，否则显示"X 分钟" */
    private String formatDuration(int seconds) {
        if (seconds < 60) {
            return seconds + " 秒";
        }
        return (seconds / 60) + " 分钟";
    }

    private void updateStatus() {
        // 自动继续
        btnAutoStart.setText(pref.isAutoStart() ? "自动继续：已开启" : "自动继续：已关闭");

        // 当前题库
        if (tvWatchTime != null) {
            String bankLabel = questionBank != null ? questionBank.getLabel(pref.getBankId()) : "";
            tvWatchTime.setText("当前题库：" + bankLabel + "｜观看时长：" + formatDuration(pref.getWatchLimitSeconds()));
        }

        // 解锁题数
        tvUnlockCount.setText("解锁题数：" + pref.getUnlockCount() + " 道连续答对");

        // 状态
        if (pref.isLocked()) {
            tvStatus.setText("当前状态：已锁屏");
            tvStatus.setTextColor(getResources().getColor(R.color.wrong_red));
            tvRemaining.setText("请答题解锁");
        } else if (pref.isTimerActive()) {
            long remaining = pref.getRemainingMillis();
            if (remaining <= 0) {
                tvStatus.setText("当前状态：时间到");
                tvStatus.setTextColor(getResources().getColor(R.color.wrong_red));
            } else {
                tvStatus.setText("当前状态：计时中");
                tvStatus.setTextColor(getResources().getColor(R.color.correct_green));
                long totalSec = remaining / 1000;
                long min = totalSec / 60;
                long sec = totalSec % 60;
                tvRemaining.setText("剩余时间：" + String.format("%02d:%02d", min, sec));
            }
        } else {
            tvStatus.setText("当前状态：未计时");
            tvStatus.setTextColor(getResources().getColor(R.color.text_secondary));
            tvRemaining.setText("");
        }
    }

    private void toast(String msg) {
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show();
    }
}
