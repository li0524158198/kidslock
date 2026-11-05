#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA R: v1.5.1 全流程回归（dist APK 1.5.1 + APK 内嵌题库映射）
   覆盖：安装/切库/计时自愈(P2-2修复验证)/30s锁屏/HOME/BACK/强杀/答题/PIN/重启"""
import json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qaenv import adb as QADB, SERIAL as QSER, TMP as QTMP, ROOT as QROOT

ADB = QADB()  # qaenv.adb 是函数，需调用取路径
SER = QSER
TMP = QTMP
APK = str(QROOT / 'dist' / 'kidslock-release-universal.apk')
# 用 APK 实际内嵌的题库做答案映射（dist 产物可能落后于 data/ 源）
QJ = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp', 'apk_questions.json'), encoding='utf-8'))

results = []
def report(name, ok, detail=''):
    results.append((name, ok, detail))
    print(('PASS' if ok else 'FAIL') + f' | {name}' + (f' | {detail}' if detail else ''), flush=True)

def sh(cmd, timeout=40):
    return subprocess.run([ADB, '-s', SER, 'shell', cmd], capture_output=True, timeout=timeout).stdout.decode('utf-8', 'ignore')

def dump():
    subprocess.run([ADB, '-s', SER, 'shell', 'uiautomator dump /sdcard/ui.xml'], capture_output=True, timeout=40)
    subprocess.run([ADB, '-s', SER, 'pull', '/sdcard/ui.xml', TMP + '/rg.xml'], capture_output=True, timeout=40)
    try:
        data = open(TMP + '/rg.xml', encoding='utf-8').read()
    except Exception:
        return []
    return [(m.group(1), (int(m.group(2)) + int(m.group(4))) // 2, (int(m.group(3)) + int(m.group(5))) // 2)
            for m in re.finditer(r'text="([^"]{1,80})"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', data) if m.group(1).strip()]

def tap(x, y, wait=1.0):
    subprocess.run([ADB, '-s', SER, 'shell', f'input tap {x} {y}'], capture_output=True, timeout=30)
    time.sleep(wait)

def key(k, wait=1.0):
    subprocess.run([ADB, '-s', SER, 'shell', f'input keyevent {k}'], capture_output=True, timeout=30)
    time.sleep(wait)

def swipe(x1, y1, x2, y2):
    subprocess.run([ADB, '-s', SER, 'shell', f'input swipe {x1} {y1} {x2} {y2} 300'], capture_output=True, timeout=30)
    time.sleep(1.2)

def focus():
    return sh('dumpsys window | grep mCurrentFocus')

def in_lock():
    return 'LockScreenActivity' in focus()

def service_running():
    out = sh('dumpsys activity services com.kidslock.app')
    return 'ServiceRecord' in out and 'LockService' in out

def scroll_top():
    for _ in range(6):
        if any(t == '儿童锁屏设置' for t, x, y in dump()):
            return True
        swipe(640, 200, 640, 600)
    return False

def tap_text(exact=None, contains=None, tries=6):
    scroll_top()
    for _ in range(tries):
        items = dump()
        for t, x, y in items:
            if (exact and t == exact) or (contains and contains in t):
                tap(x, y)
                return True
        swipe(640, 550, 640, 250)
    return False

def bank_label():
    scroll_top()
    for _ in range(5):
        for t, x, y in dump():
            if t.startswith('当前题库：'):
                return t
        swipe(640, 550, 640, 250)
    return ''

def pin_digits():
    return {t: (x, y) for t, x, y in dump() if t in '0123456789'}

def type_pin(pin, wait=0.3):
    d = pin_digits()
    if len(d) < 10:
        return False
    for c in pin:
        tap(d[c][0], d[c][1], wait)
    return True

def unlock_pin():
    if not tap_text(exact='家长解锁'):
        return False
    time.sleep(1.5)
    if not type_pin('1234'):
        return False
    time.sleep(2.2)
    return not in_lock()

def ensure_unlocked():
    sh('input keyevent KEYCODE_WAKEUP')
    sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(2.5)
    if in_lock():
        unlock_pin(); time.sleep(1)
        sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(2)
    return not in_lock()

def lock_now(retries=3):
    for _ in range(retries):
        tap_text(exact='立即锁屏'); time.sleep(3)
        if in_lock():
            return True
    return False

# ===== R1 安装与版本 =====
sh('settings put secure screensaver_enabled 0')
r = subprocess.run([ADB, '-s', SER, 'install', '-r', APK], capture_output=True, timeout=120)
report('R1a 安装 release APK', b'Success' in r.stdout)
ver = sh('dumpsys package com.kidslock.app | grep versionName').strip()
vc = sh('dumpsys package com.kidslock.app | grep versionCode').strip()
report('R1b 版本 1.5.1 / code 6', 'versionName=1.5.1' in ver and ('=6' in vc or '= 6' in vc), ver + ' | ' + vc)
ensure_unlocked()

# ===== R2 切库 =====
for sub, grade, expect in [('语文', '三', '语文·三年级'), ('数学', '五', '数学·五年级'), ('英语', '高三', '英语·高三')]:
    tap_text(exact=sub); time.sleep(0.6)
    tap_text(exact=grade); time.sleep(1.2)
    lbl = bank_label()
    report(f'R2 切换{expect}', expect in lbl, lbl)

# ===== R3 计时自愈（P2-2 修复验证）=====
ensure_unlocked()
tap_text(exact='30分钟'); time.sleep(0.6)
tap_text(exact='开始计时'); time.sleep(2)
svc1 = service_running()
sh('am force-stop com.kidslock.app'); time.sleep(2)
sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(4)
svc2 = service_running()
report('R3a 计时启动服务运行', svc1)
report('R3b 强杀重开服务自愈（P2-2 修复）', svc2, f'svc={svc2}')
tap_text(exact='停止计时'); time.sleep(1.5)

# ===== R4 30 秒计时→自动锁屏 =====
ensure_unlocked()
ok30 = tap_text(exact='30秒')
lbl = bank_label()
report('R4a 30 秒档生效', ok30 and '30 秒' in lbl, lbl)
ok_start = tap_text(exact='开始计时')
time.sleep(2.5)
report('R4b 服务运行', ok_start and service_running())
t0 = time.time()
locked = False
while time.time() - t0 < 75:
    if in_lock():
        locked = True; break
    time.sleep(3)
report('R4c 30 秒到时自动锁屏', locked, f'{time.time() - t0:.0f}s')

if locked:
    # ===== R5 HOME/BACK =====
    key('KEYCODE_HOME', wait=6)
    report('R5a HOME 回拉', in_lock(), focus()[:50])
    key('KEYCODE_BACK', wait=2)
    report('R5b BACK 拦截', in_lock())
    # ===== R6 强杀保持 =====
    sh('am force-stop com.kidslock.app'); time.sleep(2)
    sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(4)
    report('R6 强杀重启锁屏保持', in_lock(), focus()[:50])

    # ===== R7 答题（切语文·三）=====
    unlock_pin()
    tap_text(exact='语文'); time.sleep(0.6)
    tap_text(exact='三'); time.sleep(1.2)
    AMAP = {}
    for it in QJ['banks']['chinese_g3']:
        AMAP[it['q']] = it['opts'][it['ans']]

    def current_q(items):
        for t, x, y in items:
            if t in AMAP:
                return t
        return None

    report('R7-pre 立即锁屏', lock_now())
    items = dump()
    q = current_q(items)
    if q:
        correct = AMAP[q]
        wrong = next(((x, y) for t, x, y in items if t != correct and len(t) <= 40
                      and t not in ('屏幕已锁定', '家长解锁', '语文·三年级') and '已答对' not in t), None)
        if wrong:
            tap(wrong[0], wrong[1], 3.2)
            prog = [t for t, x, y in dump() if '已答对' in t]
            report('R7a 答错归零出新题', any('0/3' in t for t in prog), str(prog))
        else:
            report('R7a 答错归零出新题', False, '无干扰项')
    else:
        report('R7a 答错归零出新题', False, f'q={q}')

    t0 = time.time()
    unlocked = False
    n = 0
    while time.time() - t0 < 150:
        if not in_lock():
            unlocked = True; break
        items = dump()
        q = current_q(items)
        if not q:
            time.sleep(1.5); continue
        p = next(((x, y) for t, x, y in items if t == AMAP[q]), None)
        if p:
            tap(p[0], p[1], 3.4); n += 1
    report('R7b 连对 3 题自动解锁', unlocked, f'{n} 次')
    # 自动继续（新功能）：答题解锁后若"自动继续"开启 → 自动开始新一轮计时
    if unlocked:
        time.sleep(3)
        svc = service_running()
        status = ''
        scroll_top()
        for t, x, y in dump():
            if t.startswith('当前状态'):
                status = t
        report('R7c 自动继续（解锁后自动计时，新功能）', svc and '计时中' in status, f'svc={svc} {status}')

    # ===== R8 PIN =====
    ensure_unlocked()
    report('R8-pre 立即锁屏', lock_now())
    tap_text(exact='家长解锁'); time.sleep(1.8)
    t_lock = None
    for i in range(5):
        type_pin('9999')
        time.sleep(1.6)
        if i == 4:
            t_lock = time.time()
    report('R8a 连错 5 次仍锁屏', in_lock())
    type_pin('1234'); time.sleep(2.2)
    report('R8b 锁定期内正确 PIN 被拒', in_lock())
    remain = 31 - (time.time() - t_lock)
    if remain > 0:
        time.sleep(remain + 1)
    if not pin_digits():
        tap_text(exact='家长解锁'); time.sleep(1.5)
    ok = type_pin('1234'); time.sleep(2.5)
    report('R8c 锁定期满正确 PIN 解锁', ok and not in_lock())

# ===== R9 设备重启 =====
ensure_unlocked()
report('R9-pre 立即锁屏', lock_now())
subprocess.run([ADB, '-s', SER, 'reboot'], capture_output=True, timeout=30)
t0 = time.time(); back = False
while time.time() - t0 < 360:
    time.sleep(12)
    try:
        r = subprocess.run([ADB, '-s', SER, 'shell', 'getprop sys.boot_completed'],
                           capture_output=True, timeout=20)
        if r.returncode == 0 and r.stdout.decode().strip() == '1':
            back = True; break
    except Exception:
        pass
report('R9a 设备重启完成', back, f'{time.time() - t0:.0f}s')
if back:
    time.sleep(12)
    report('R9b 重启后锁屏自动恢复（BootReceiver）', in_lock(), focus()[:50])
    if in_lock():
        ok = unlock_pin()
        report('R9c 重启后 PIN 解锁', ok)

print('\n========== 回归汇总 ==========')
p = sum(1 for _, ok, _ in results if ok)
for n, ok, d in results:
    print(('PASS' if ok else 'FAIL') + ' | ' + n + (' | ' + d if d else ''))
print(f'===== v1.5.1 回归: {p} PASS / {len(results) - p} FAIL =====')
sys.exit(0 if p == len(results) else 1)
