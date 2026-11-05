package com.kidslock.app;

import android.app.UiModeManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.res.Configuration;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;

/**
 * SharedPreferences 封装：管理所有持久化设置和状态。
 * 状态在重启后仍然保留，保证锁屏不会被绕过。
 */
public class PrefManager {

    private static final String PREF_NAME = "kids_lock_prefs";
    private final SharedPreferences prefs;

    // Keys
    private static final String KEY_AUTO_START = "auto_start";
    private static final String KEY_WATCH_LIMIT_MIN = "watch_limit_min";
    private static final String KEY_WATCH_LIMIT_SEC = "watch_limit_sec";
    private static final String KEY_UNLOCK_COUNT = "unlock_count";
    private static final String KEY_BANK_ID = "bank_id";
    private static final String KEY_IS_LOCKED = "is_locked";
    private static final String KEY_TIMER_ACTIVE = "timer_active";
    private static final String KEY_TIMER_END_TIME = "timer_end_time";
    private static final String KEY_PARENT_PIN = "parent_pin"; // 旧版明文，仅用于迁移读取
    private static final String KEY_PIN_CRED = "pin_cred";     // "saltHex:hashHex"
    private static final String KEY_PIN_IS_DEFAULT = "pin_is_default";
    private static final String KEY_PIN_FAIL_COUNT = "pin_fail_count";
    private static final String KEY_PIN_LOCK_UNTIL = "pin_lock_until";

    private static final int SALT_HEX_LEN = 32; // 16 字节
    private static final SecureRandom SECURE_RANDOM = new SecureRandom();

    // Defaults
    private static final boolean DEFAULT_AUTO_START = true;
    private static final int DEFAULT_WATCH_LIMIT_MIN = 30;
    private static final int DEFAULT_UNLOCK_COUNT = 3;
    private static final String DEFAULT_PARENT_PIN = "1234";
    private static final int MAX_PIN_FAILS = 5;
    private static final long PIN_LOCKOUT_MS = 30_000;

    public PrefManager(Context context) {
        prefs = context.getApplicationContext().getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
    }

    // --- Auto Start ---
    public boolean isAutoStart() {
        return prefs.getBoolean(KEY_AUTO_START, DEFAULT_AUTO_START);
    }

    public void setAutoStart(boolean enabled) {
        prefs.edit().putBoolean(KEY_AUTO_START, enabled).apply();
    }

    // --- Watch Limit（单位：秒，支持 30 秒测试档；兼容旧版"分钟"存储）---
    public int getWatchLimitSeconds() {
        int sec = prefs.getInt(KEY_WATCH_LIMIT_SEC, -1);
        if (sec < 0) {
            // 迁移旧版分钟值
            sec = prefs.getInt(KEY_WATCH_LIMIT_MIN, DEFAULT_WATCH_LIMIT_MIN) * 60;
            setWatchLimitSeconds(sec);
        }
        return sec;
    }

    public void setWatchLimitSeconds(int seconds) {
        prefs.edit().putInt(KEY_WATCH_LIMIT_SEC, seconds).apply();
    }

    // --- Unlock Question Count ---
    public int getUnlockCount() {
        return prefs.getInt(KEY_UNLOCK_COUNT, DEFAULT_UNLOCK_COUNT);
    }

    public void setUnlockCount(int count) {
        prefs.edit().putInt(KEY_UNLOCK_COUNT, count).apply();
    }

    // --- 题库选择（人教版 学科×学段）---
    public String getBankId() {
        return prefs.getString(KEY_BANK_ID, "chinese_primary");
    }

    public void setBankId(String bankId) {
        prefs.edit().putString(KEY_BANK_ID, bankId).apply();
    }

    // --- Lock State ---
    public boolean isLocked() {
        return prefs.getBoolean(KEY_IS_LOCKED, false);
    }

    public void setLocked(boolean locked) {
        prefs.edit().putBoolean(KEY_IS_LOCKED, locked).apply();
    }

    // --- Timer ---
    public boolean isTimerActive() {
        return prefs.getBoolean(KEY_TIMER_ACTIVE, false);
    }

    public void setTimerActive(boolean active) {
        prefs.edit().putBoolean(KEY_TIMER_ACTIVE, active).apply();
    }

    public long getTimerEndTime() {
        return prefs.getLong(KEY_TIMER_END_TIME, 0);
    }

    public void setTimerEndTime(long endTime) {
        prefs.edit().putLong(KEY_TIMER_END_TIME, endTime).apply();
    }

    public long getRemainingMillis() {
        long end = getTimerEndTime();
        long now = System.currentTimeMillis();
        return Math.max(0, end - now);
    }

    // --- Parent PIN（加盐 SHA-256 哈希存储）---
    // 存储格式 pin_cred = "<saltHex32>:<hashHex64>"，hash = SHA256(saltHex + pin)。
    // 旧版明文（parent_pin，4 位数字）在首次校验时自动迁移为哈希后删除；默认 PIN 1234。

    /** 设置 PIN（存哈希，明文不落盘）。 */
    public void setParentPin(String pin) {
        String salt = randomHex();
        prefs.edit()
                .putString(KEY_PIN_CRED, salt + ":" + sha256Hex(salt + pin))
                .putBoolean(KEY_PIN_IS_DEFAULT, false)
                .apply();
    }

    /** 校验 PIN（首次调用会把旧明文/默认 1234 迁移为哈希）。 */
    public boolean checkPin(String pin) {
        migrateOrInit();
        String cred = prefs.getString(KEY_PIN_CRED, "");
        int i = cred.indexOf(':');
        if (i <= 0) return false;
        return sha256Hex(cred.substring(0, i) + pin).equals(cred.substring(i + 1));
    }

    /** 是否仍是默认 PIN（1234，从未被修改过）——供设置页提示。 */
    public boolean isPinDefault() {
        migrateOrInit();
        return prefs.getBoolean(KEY_PIN_IS_DEFAULT, false);
    }

    /** 生成 pin_cred 哈希凭据：优先迁移旧明文，否则初始化默认 1234。 */
    private void migrateOrInit() {
        if (prefs.getString(KEY_PIN_CRED, null) != null) return;
        String legacy = prefs.getString(KEY_PARENT_PIN, null);
        boolean legacyValid = legacy != null && legacy.matches("\\d{4}");
        String base = legacyValid ? legacy : DEFAULT_PARENT_PIN;
        String salt = randomHex();
        prefs.edit()
                .putString(KEY_PIN_CRED, salt + ":" + sha256Hex(salt + base))
                .putBoolean(KEY_PIN_IS_DEFAULT, !legacyValid)
                .remove(KEY_PARENT_PIN)
                .apply();
    }

    private static String randomHex() {
        StringBuilder sb = new StringBuilder(SALT_HEX_LEN);
        for (int i = 0; i < SALT_HEX_LEN; i++) sb.append("0123456789abcdef".charAt(SECURE_RANDOM.nextInt(16)));
        return sb.toString();
    }

    private static String sha256Hex(String s) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            StringBuilder sb = new StringBuilder(64);
            for (byte b : md.digest(s.getBytes(StandardCharsets.UTF_8))) sb.append(String.format("%02x", b));
            return sb.toString();
        } catch (Exception e) {
            throw new IllegalStateException("SHA-256 unavailable", e);
        }
    }

    // --- PIN 防暴力尝试 ---
    public boolean isPinLocked() {
        return System.currentTimeMillis() < prefs.getLong(KEY_PIN_LOCK_UNTIL, 0);
    }

    public long getPinLockRemainingMillis() {
        long until = prefs.getLong(KEY_PIN_LOCK_UNTIL, 0);
        return Math.max(0, until - System.currentTimeMillis());
    }

    public void recordPinFailure() {
        int fails = prefs.getInt(KEY_PIN_FAIL_COUNT, 0) + 1;
        if (fails >= MAX_PIN_FAILS) {
            prefs.edit()
                    .putInt(KEY_PIN_FAIL_COUNT, 0)
                    .putLong(KEY_PIN_LOCK_UNTIL, System.currentTimeMillis() + PIN_LOCKOUT_MS)
                    .apply();
        } else {
            prefs.edit().putInt(KEY_PIN_FAIL_COUNT, fails).apply();
        }
    }

    public void resetPinFailures() {
        prefs.edit().putInt(KEY_PIN_FAIL_COUNT, 0).putLong(KEY_PIN_LOCK_UNTIL, 0).apply();
    }

    // --- Helper: start timer（参数：秒）---
    public void startTimer(int seconds) {
        long endTime = System.currentTimeMillis() + (long) seconds * 1000;
        setTimerActive(true);
        setTimerEndTime(endTime);
        setLocked(false);
    }

    public void stopTimer() {
        setTimerActive(false);
        setTimerEndTime(0);
    }

    public boolean isTimerExpired() {
        return isTimerActive() && System.currentTimeMillis() >= getTimerEndTime();
    }

    /**
     * 启用/禁用 HOME launcher alias。
     * 锁屏时启用，让按 HOME 键回到锁屏界面。
     * 解锁时禁用，让按 HOME 键回到正常电视桌面。
     * 注意：仅电视设备启用（手机/平板上启用会顶掉系统默认桌面，
     * 且手机系统本身不允许第三方应用拦截 HOME，启用无益反而干扰）。
     */
    public void setHomeAliasEnabled(Context context, boolean enabled) {
        if (!isTvDevice(context)) {
            return;
        }
        ComponentName alias = new ComponentName(context, "com.kidslock.app.LockScreenHome");
        PackageManager pm = context.getPackageManager();
        int state = enabled
                ? PackageManager.COMPONENT_ENABLED_STATE_ENABLED
                : PackageManager.COMPONENT_ENABLED_STATE_DISABLED;
        pm.setComponentEnabledSetting(alias, state, PackageManager.DONT_KILL_APP);
    }

    /** 判断是否电视设备（Leanback/TELEVISION UI 模式） */
    public boolean isTvDevice(Context context) {
        UiModeManager uiModeManager = (UiModeManager) context.getSystemService(Context.UI_MODE_SERVICE);
        if (uiModeManager != null
                && uiModeManager.getCurrentModeType() == Configuration.UI_MODE_TYPE_TELEVISION) {
            return true;
        }
        PackageManager pm = context.getPackageManager();
        return pm.hasSystemFeature(PackageManager.FEATURE_LEANBACK);
    }
}
