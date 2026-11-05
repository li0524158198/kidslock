#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA E10: 设备重启 → BootReceiver 恢复锁屏（独立执行，避免影响主 E2E）"""
import re, subprocess, sys, time

from qaenv import adb, SERIAL as SER, TMP
ADB = adb()

def sh(cmd, timeout=40):
    return subprocess.run([ADB, '-s', SER, 'shell', cmd], capture_output=True, timeout=timeout).stdout.decode('utf-8', 'ignore')

def dump():
    subprocess.run([ADB, '-s', SER, 'shell', 'uiautomator dump /sdcard/ui.xml'], capture_output=True, timeout=40)
    subprocess.run([ADB, '-s', SER, 'pull', '/sdcard/ui.xml', TMP + '/rb.xml'], capture_output=True, timeout=40)
    try:
        data = open(TMP + '/rb.xml', encoding='utf-8').read()
    except Exception:
        return []
    return [(m.group(1), (int(m.group(2)) + int(m.group(4))) // 2, (int(m.group(3)) + int(m.group(5))) // 2)
            for m in re.finditer(r'text="([^"]{1,80})"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', data) if m.group(1).strip()]

def tap(x, y, wait=1.0):
    subprocess.run([ADB, '-s', SER, 'shell', f'input tap {x} {y}'], capture_output=True, timeout=30)
    time.sleep(wait)

def swipe(x1, y1, x2, y2):
    subprocess.run([ADB, '-s', SER, 'shell', f'input swipe {x1} {y1} {x2} {y2} 300'], capture_output=True, timeout=30)
    time.sleep(1.0)

def focus():
    return sh('dumpsys window | grep mCurrentFocus')

def in_lock():
    return 'LockScreenActivity' in focus()

def tap_text(exact):
    for _ in range(3):
        if not any(t == '儿童锁屏设置' for t, x, y in dump()):
            swipe(640, 200, 640, 600)
    for _ in range(6):
        for t, x, y in dump():
            if t == exact:
                tap(x, y)
                return True
        swipe(640, 550, 640, 250)
    return False

# 前置：确保未锁 → 立即锁屏
sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(3)
if in_lock():
    print('当前已锁，先 PIN 解锁')
    tap_text('家长解锁'); time.sleep(1.5)
    digits = {}
    for t, x, y in dump():
        if t in '0123456789':
            digits[t] = (x, y)
    for d in '1234':
        if d in digits:
            tap(*digits[d], wait=0.35)
    time.sleep(2)
    sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(2)
ok_lock = tap_text('立即锁屏'); time.sleep(3)
print('E10-pre 锁屏成功:', in_lock(), '(点击立即锁屏:', ok_lock, ')')
assert in_lock(), '未能进入锁屏，中止重启测试'

print('E10a 重启设备...')
subprocess.run([ADB, '-s', SER, 'reboot'], capture_output=True, timeout=30)
# 等待 bootloader → offline → online
t0 = time.time()
back = False
while time.time() - t0 < 360:
    time.sleep(12)
    try:
        r = subprocess.run([ADB, '-s', SER, 'shell', 'getprop sys.boot_completed'],
                           capture_output=True, timeout=20)
        if r.returncode == 0 and r.stdout.decode().strip() == '1':
            back = True
            break
    except Exception:
        pass
print(f'{"PASS" if back else "FAIL"} | E10b 设备重启完成 @ {time.time()-t0:.0f}s')

if back:
    time.sleep(12)  # 给 BootReceiver / HOME alias 生效时间
    f = focus()
    locked = in_lock()
    # BootReceiver 直接 startActivity 可能被系统限制，悬浮窗/服务兜底也可；检查通知与前台
    svc = 'ServiceRecord' in sh('dumpsys activity services com.kidslock.app')
    print(f'{"PASS" if locked else "FAIL"} | E10c 重启后锁屏自动恢复 | focus={f[:60]} svc={svc}')
    if not locked:
        # 点开应用看是否被重定向到锁屏（alias/状态恢复路径）
        sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(3)
        redirected = in_lock()
        print(f'{"PASS" if redirected else "FAIL"} | E10c-2 打开应用被重定向到锁屏（状态持久化） | {focus()[:60]}')
    else:
        # PIN 解锁收尾
        tap_text('家长解锁'); time.sleep(1.5)
        digits = {}
        for t, x, y in dump():
            if t in '0123456789':
                digits[t] = (x, y)
        ok = False
        if len(digits) >= 10:
            for d in '1234':
                tap(*digits[d], wait=0.35)
            time.sleep(2.5)
            ok = not in_lock()
        print(f'{"PASS" if ok else "FAIL"} | E10d 重启后 PIN 解锁')
