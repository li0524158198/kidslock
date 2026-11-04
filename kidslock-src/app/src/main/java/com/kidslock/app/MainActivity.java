package com.kidslock.app;

import android.app.AlertDialog;
import android.content.DialogInterface;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

/**
 * 设置主界面。
 * 家长可以在这里配置：开机自启、观看时长、解锁题数、家长PIN码。
 * 还可以开始/停止计时、立即锁屏、查看剩余时间。
 */
public class MainActivity extends AppCompatActivity {

    private PrefManager pref;
    private final Handler handler = new Handler(Looper.getMainLooper());

    private TextView tvStatus;
    private TextView tvRemaining;
    private Button btnAutoStart;
    private TextView tvWatchTime;
    private TextView tvUnlockCount;
    private Button[] bankButtons;

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

        // 题库选择 3×3 网格（人教版 学科×学段）
        QuestionBank qb = new QuestionBank(this);
        int[] bankIds = {R.id.bank00, R.id.bank01, R.id.bank02, R.id.bank10, R.id.bank11,
                R.id.bank12, R.id.bank20, R.id.bank21, R.id.bank22};
        bankButtons = new Button[bankIds.length];
        for (int i = 0; i < bankIds.length; i++) {
            Button b = findViewById(bankIds[i]);
            b.setText(qb.getLabel(QuestionBank.BANK_IDS[i]));
            b.setOnClickListener(v -> {
                pref.setBankId((String) v.getTag());
                updateStatus();
                toast("题库已切换");
            });
            b.setTag(QuestionBank.BANK_IDS[i]);
            bankButtons[i] = b;
        }
    }

    private void setupListeners() {
        // 开机自启
        btnAutoStart.setOnClickListener(v -> {
            boolean newVal = !pref.isAutoStart();
            pref.setAutoStart(newVal);
            updateStatus();
            toast(newVal ? "已开启开机自启" : "已关闭开机自启");
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
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
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
        // 开机自启
        btnAutoStart.setText(pref.isAutoStart() ? "开机自启：已开启" : "开机自启：已关闭");

        // 题库选中态高亮
        String current = pref.getBankId();
        for (Button b : bankButtons) {
            boolean sel = current.equals(b.getTag());
            b.setBackgroundResource(sel ? R.drawable.btn_bank_selected : R.drawable.btn_settings_bg);
            b.setTextColor(sel ? 0xFF2A9D5C : 0xFFE0E1DD);
        }

        // 观看时长
        tvWatchTime.setText("观看时长：" + formatDuration(pref.getWatchLimitSeconds()));

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
