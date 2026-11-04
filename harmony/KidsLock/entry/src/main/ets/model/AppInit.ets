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
    PersistentStorage.persistProp('parentPin', '1234');
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
