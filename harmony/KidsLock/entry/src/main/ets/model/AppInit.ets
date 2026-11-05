import { sha256Hex } from './Sha256';

/**
 * 持久化状态管理：基于 AppStorage + PersistentStorage。
 * 状态在 App 重启后仍然保留，保证锁屏不会被绕过。
 */
export class AppInit {
  private static inited: boolean = false;

  public static init(): void {
    if (AppInit.inited) {
      return;
    }
    AppInit.inited = true;
    // 锁屏/计时状态持久化，重启 App（甚至重启设备）后仍然生效
    PersistentStorage.persistProp('isLocked', false);
    PersistentStorage.persistProp('timerActive', false);
    PersistentStorage.persistProp('timerEndTime', 0);
    PersistentStorage.persistProp('autoStart', true);
    PersistentStorage.persistProp('watchLimitSeconds', 1800);
    PersistentStorage.persistProp('bankId', 'chinese_primary');
    PersistentStorage.persistProp('unlockCount', 3);
    PersistentStorage.persistProp('pinCred', '');
    PersistentStorage.persistProp('pinIsDefault', true);
    // 旧版明文 PIN 载体：仅供迁移读取（4 位数字 = 旧自定义 PIN），迁移后清空
    PersistentStorage.persistProp('parentPin', '');
    PersistentStorage.persistProp('pinFailCount', 0);
    PersistentStorage.persistProp('pinLockUntil', 0);
  }

  public static isLocked(): boolean {
    const v = AppStorage.get<boolean>('isLocked');
    return v === undefined ? false : v;
  }

  public static now(): number {
    return new Date().getTime();
  }

  public static getTimerEndTime(): number {
    const v = AppStorage.get<number>('timerEndTime');
    return v === undefined ? 0 : v;
  }

  public static remainingMillis(): number {
    const end = AppInit.getTimerEndTime();
    return Math.max(0, end - AppInit.now());
  }

  public static isTimerExpired(): boolean {
    const active = AppStorage.get<boolean>('timerActive') ?? false;
    return active && AppInit.now() >= AppInit.getTimerEndTime();
  }

  public static startTimer(seconds: number): void {
    AppStorage.setOrCreate('timerEndTime', AppInit.now() + seconds * 1000);
    AppStorage.setOrCreate('timerActive', true);
    AppStorage.setOrCreate('isLocked', false);
  }

  public static stopTimer(): void {
    AppStorage.setOrCreate('timerActive', false);
    AppStorage.setOrCreate('timerEndTime', 0);
  }

  public static unlockAll(): void {
    AppStorage.setOrCreate('isLocked', false);
    AppInit.stopTimer();
    AppStorage.setOrCreate('pinFailCount', 0);
    AppStorage.setOrCreate('pinLockUntil', 0);
  }

  // ---- 家长 PIN（加盐 SHA-256 哈希存储，P2-3）----
  // pinCred = "<saltHex32>:<hashHex64>"，hash = SHA256(saltHex + pin)。
  // 旧版明文（parentPin，4 位数字）首次校验时自动迁移为哈希后清空；默认 PIN 1234。

  /** 设置 PIN（存哈希，明文不落盘）。 */
  public static setParentPin(pin: string): void {
    const salt = AppInit.randomSaltHex();
    AppStorage.setOrCreate('pinCred', salt + ':' + sha256Hex(salt + pin));
    AppStorage.setOrCreate('pinIsDefault', false);
  }

  /** 校验 PIN（首次调用会把旧明文/默认 1234 迁移为哈希）。 */
  public static checkPin(pin: string): boolean {
    AppInit.migrateOrInit();
    const cred = AppStorage.get<string>('pinCred') ?? '';
    const i = cred.indexOf(':');
    if (i <= 0) {
      return false;
    }
    return sha256Hex(cred.substring(0, i) + pin) === cred.substring(i + 1);
  }

  /** 是否仍是默认 PIN（1234，从未被修改过）——供设置页提示。 */
  public static isPinDefault(): boolean {
    AppInit.migrateOrInit();
    return AppStorage.get<boolean>('pinIsDefault') ?? true;
  }

  /** 生成 pin_cred 哈希凭据：优先迁移旧明文，否则初始化默认 1234。 */
  private static migrateOrInit(): void {
    const cred = AppStorage.get<string>('pinCred') ?? '';
    if (cred.includes(':')) {
      return;
    }
    const legacy = AppStorage.get<string>('parentPin') ?? '';
    const legacyValid = /^[0-9]{4}$/.test(legacy);
    const base = legacyValid ? legacy : '1234';
    AppInit.setParentPin(base);
    AppStorage.setOrCreate('pinIsDefault', !legacyValid);
    if (legacy.length > 0) {
      AppStorage.setOrCreate('parentPin', '');
    }
  }

  private static randomSaltHex(): string {
    let s = '';
    for (let i = 0; i < 32; i++) {
      s += Math.floor(Math.random() * 16).toString(16);
    }
    return s;
  }

  // ---- PIN 防暴力尝试 ----

  public static isPinLocked(): boolean {
    const until = AppStorage.get<number>('pinLockUntil') ?? 0;
    return AppInit.now() < until;
  }

  public static pinLockRemainingMillis(): number {
    const until = AppStorage.get<number>('pinLockUntil') ?? 0;
    return Math.max(0, until - AppInit.now());
  }

  public static recordPinFailure(): void {
    const fails = (AppStorage.get<number>('pinFailCount') ?? 0) + 1;
    if (fails >= 5) {
      AppStorage.setOrCreate('pinFailCount', 0);
      AppStorage.setOrCreate('pinLockUntil', AppInit.now() + 30000);
    } else {
      AppStorage.setOrCreate('pinFailCount', fails);
    }
  }

  public static resetPinFailures(): void {
    AppStorage.setOrCreate('pinFailCount', 0);
    AppStorage.setOrCreate('pinLockUntil', 0);
  }
}
