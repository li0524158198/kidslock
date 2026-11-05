import Foundation
import Combine
import CryptoKit
import UserNotifications

/// UserDefaults 封装：管理所有持久化设置和状态。
/// 状态在 App 重启后仍然保留，保证锁屏不会被绕过。
final class Prefs: ObservableObject {

    static let shared = Prefs()

    private let d = UserDefaults.standard

    // Keys
    private enum Key {
        static let autoStart = "auto_start"
        static let watchLimitSec = "watch_limit_sec"
        static let unlockCount = "unlock_count"
        static let bankId = "bank_id"
        static let isLocked = "is_locked"
        static let timerActive = "timer_active"
        static let timerEndTime = "timer_end_time"
        static let parentPin = "parent_pin"   // 旧版明文，仅用于迁移读取
        static let pinCred = "pin_cred"       // "saltHex:hashHex"
        static let pinIsDefault = "pin_is_default"
        static let pinFailCount = "pin_fail_count"
        static let pinLockUntil = "pin_lock_until"
    }

    // Defaults
    private let defaultWatchLimitSec = 1800
    private let defaultUnlockCount = 3
    private let defaultParentPin = "1234"
    private let maxPinFails = 5
    private let pinLockoutMs: Double = 30_000

    // MARK: - Auto Start（iOS 上映射为：重新打开 App 时自动继续计时/锁屏）

    @Published var autoStart: Bool {
        didSet { d.set(autoStart, forKey: Key.autoStart) }
    }

    // MARK: - Watch Limit（单位：秒，支持 30 秒测试档）

    @Published var watchLimitSeconds: Int {
        didSet { d.set(watchLimitSeconds, forKey: Key.watchLimitSec) }
    }

    /// 时长格式化：<60 秒显示"X 秒"，否则"X 分钟"
    func formatDuration(_ seconds: Int) -> String {
        seconds < 60 ? "\(seconds) 秒" : "\(seconds / 60) 分钟"
    }

    // MARK: - Unlock Question Count

    @Published var unlockCount: Int {
        didSet { d.set(unlockCount, forKey: Key.unlockCount) }
    }

    // MARK: - Lock State

    @Published var isLocked: Bool {
        didSet { d.set(isLocked, forKey: Key.isLocked) }
    }

    // MARK: - Timer

    @Published var timerActive: Bool {
        didSet { d.set(timerActive, forKey: Key.timerActive) }
    }

    var timerEndTime: Double {
        get { d.double(forKey: Key.timerEndTime) }
        set { d.set(newValue, forKey: Key.timerEndTime) }
    }

    var remainingMillis: Double {
        max(0, timerEndTime - Date().timeIntervalSince1970 * 1000)
    }

    var isTimerExpired: Bool {
        timerActive && Date().timeIntervalSince1970 * 1000 >= timerEndTime
    }

    // MARK: - 题库选择（人教版 学科×年级 / 自定义）

    @Published var bankId: String {
        didSet { d.set(bankId, forKey: Key.bankId) }
    }

    // MARK: - Parent PIN（加盐 SHA-256 哈希存储）
    // pinCred = "<saltHex>:<hashHex>"，hash = SHA256(saltHex + pin)。
    // 旧版明文（parent_pin，4 位数字）首次校验时自动迁移为哈希后删除；默认 PIN 1234。

    /// 设置 PIN（存哈希，明文不落盘）。
    func setParentPin(_ pin: String) {
        var salt = ""
        for _ in 0..<32 { salt += String(format: "%x", Int.random(in: 0...15)) }
        d.set(salt + ":" + sha256Hex(salt + pin), forKey: Key.pinCred)
        d.set(false, forKey: Key.pinIsDefault)
    }

    /// 校验 PIN（首次调用会把旧明文/默认 1234 迁移为哈希）。
    func checkPin(_ pin: String) -> Bool {
        migrateOrInit()
        guard let cred = d.string(forKey: Key.pinCred),
              let i = cred.firstIndex(of: ":") else { return false }
        let salt = String(cred[cred.startIndex..<i])
        return sha256Hex(salt + pin) == String(cred[cred.index(after: i)...])
    }

    /// 是否仍是默认 PIN（1234，从未被修改过）——供设置页提示。
    var isPinDefault: Bool {
        migrateOrInit()
        return d.bool(forKey: Key.pinIsDefault)
    }

    private func migrateOrInit() {
        guard d.string(forKey: Key.pinCred) == nil else { return }
        let legacy = d.string(forKey: Key.parentPin)
        let legacyValid = legacy?.count == 4 && legacy!.allSatisfy(\.isNumber)
        setParentPin(legacyValid ? legacy! : defaultParentPin)
        d.set(!legacyValid, forKey: Key.pinIsDefault)
        d.removeObject(forKey: Key.parentPin)
    }

    private func sha256Hex(_ s: String) -> String {
        SHA256.hash(data: Data(s.utf8)).map { String(format: "%02x", $0) }.joined()
    }

    // MARK: - PIN 防暴力尝试

    var isPinLocked: Bool {
        Date().timeIntervalSince1970 * 1000 < d.double(forKey: Key.pinLockUntil)
    }

    var pinLockRemainingMillis: Double {
        max(0, d.double(forKey: Key.pinLockUntil) - Date().timeIntervalSince1970 * 1000)
    }

    func recordPinFailure() {
        let fails = d.integer(forKey: Key.pinFailCount) + 1
        if fails >= maxPinFails {
            d.set(0, forKey: Key.pinFailCount)
            d.set(Date().timeIntervalSince1970 * 1000 + pinLockoutMs, forKey: Key.pinLockUntil)
        } else {
            d.set(fails, forKey: Key.pinFailCount)
        }
    }

    func resetPinFailures() {
        d.set(0, forKey: Key.pinFailCount)
        d.set(0, forKey: Key.pinLockUntil)
    }

    // MARK: - Init（从 UserDefaults 恢复）

    private init() {
        autoStart = d.object(forKey: Key.autoStart) as? Bool ?? true
        // 兼容旧版"分钟"存储
        if let sec = d.object(forKey: Key.watchLimitSec) as? Int {
            watchLimitSeconds = sec
        } else {
            let minutes = d.object(forKey: "watch_limit_min") as? Int ?? defaultWatchLimitSec / 60
            watchLimitSeconds = minutes * 60
        }
        unlockCount = d.object(forKey: Key.unlockCount) as? Int ?? defaultUnlockCount
        bankId = d.string(forKey: Key.bankId) ?? "chinese_g1"
        isLocked = d.bool(forKey: Key.isLocked)
        timerActive = d.bool(forKey: Key.timerActive)
    }

    // MARK: - Helper

    func startTimer(seconds: Int) {
        timerEndTime = Date().timeIntervalSince1970 * 1000 + Double(seconds) * 1000
        timerActive = true
        isLocked = false
        scheduleExpiryNotification()
    }

    func stopTimer() {
        timerActive = false
        timerEndTime = 0
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
    }

    /// App 启动时恢复状态：锁屏状态优先；其次检查计时是否已超时。
    func restoreOnLaunch() {
        if isLocked { return }
        if timerActive {
            if isTimerExpired {
                timerActive = false
                isLocked = true
            } else if !autoStart {
                // 关闭了自动继续 → 取消计时
                timerActive = false
                timerEndTime = 0
            }
        }
    }

    /// 彻底解锁：清除锁屏与计时状态。
    func unlockAll() {
        isLocked = false
        stopTimer()
        resetPinFailures()
    }

    // MARK: - Local Notification（后台到点提醒）

    private func scheduleExpiryNotification() {
        let center = UNUserNotificationCenter.current()
        center.requestAuthorization(options: [.alert, .sound]) { _, _ in }
        center.removeAllPendingNotificationRequests()

        let content = UNMutableNotificationContent()
        content.title = "观看时间到了"
        content.body = "屏幕已锁定，打开儿童锁屏答题解锁"
        content.sound = .default

        let interval = max(1, remainingMillis / 1000)
        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: interval, repeats: false)
        let request = UNNotificationRequest(identifier: "kids_lock_expiry", content: content, trigger: trigger)
        center.add(request)
    }
}
