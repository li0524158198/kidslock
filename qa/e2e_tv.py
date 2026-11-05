#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA E: Android TV 模拟器全流程 E2E 实测（真实 release APK）"""
import json, re, subprocess, sys, time

from qaenv import adb, SERIAL as SER, TMP, load_questions, ROOT
ADB = adb()
APK = str(ROOT / 'dist' / 'kidslock-release-universal.apk')
J = load_questions()

results = []
def report(name, ok, detail=''):
    results.append((name, ok, detail))
    print(('PASS' if ok else 'FAIL') + f' | {name}' + (f' | {detail}' if detail else ''), flush=True)

def sh(cmd, timeout=40):
    return subprocess.run([ADB, '-s', SER, 'shell', cmd], capture_output=True, timeout=timeout).stdout.decode('utf-8', 'ignore')

def dump():
    subprocess.run([ADB, '-s', SER, 'shell', 'uiautomator dump /sdcard/ui.xml'], capture_output=True, timeout=40)
    subprocess.run([ADB, '-s', SER, 'pull', '/sdcard/ui.xml', TMP + '/e2e.xml'], capture_output=True, timeout=40)
    try:
        data = open(TMP + '/e2e.xml', encoding='utf-8').read()
    except Exception:
        return []
    out = []
    for m in re.finditer(r'text="([^"]{1,80})"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', data):
        t, x1, y1, x2, y2 = m.group(1), *map(int, m.groups()[1:])
        if t.strip():
            out.append((t, (x1 + x2) // 2, (y1 + y2) // 2))
    return out

def tap(x, y, wait=1.0):
    subprocess.run([ADB, '-s', SER, 'shell', f'input tap {x} {y}'], capture_output=True, timeout=30)
    time.sleep(wait)

def key(k, wait=1.0):
    subprocess.run([ADB, '-s', SER, 'shell', f'input keyevent {k}'], capture_output=True, timeout=30)
    time.sleep(wait)

def focus():
    return sh('dumpsys window | grep mCurrentFocus')

def in_lock():
    return 'LockScreenActivity' in focus()

def in_settings():
    return 'MainActivity' in focus()

def find(items, exact=None, contains=None):
    for t, x, y in items:
        if (exact and t == exact) or (contains and contains in t):
            return x, y
    return None

def tap_text(exact=None, contains=None, tries=3, swipe_up=False):
    for _ in range(tries):
        items = dump()
        p = find(items, exact=exact, contains=contains)
        if p:
            tap(*p)
            return True
        if swipe_up:
            sh('input swipe 640 500 640 200 300'); time.sleep(1)
    return False

def unlock_pin():
    if not tap_text(exact='家长解锁', tries=2):
        return False
    time.sleep(1.5)
    digits = {}
    for t, x, y in dump():
        if t in '0123456789':
            digits[t] = (x, y)  # PIN 键盘后出现，覆盖同名
    if len(digits) < 10:
        return False
    for d in '1234':
        tap(*digits[d], wait=0.35)
    time.sleep(2.2)
    return not in_lock()

def ensure_unlocked():
    sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(2.5)
    if in_lock():
        unlock_pin(); time.sleep(1)
        sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(2)
    return not in_lock()

def switch_bank(subject, grade_label):
    tap_text(exact=subject); time.sleep(0.6)
    return tap_text(exact=grade_label)

# ============ E1 安装与启动 ============
r = subprocess.run([ADB, '-s', SER, 'install', '-r', APK], capture_output=True, timeout=120)
ok = b'Success' in r.stdout
report('E1a 安装 release APK', ok, r.stdout.decode('utf-8', 'ignore').strip()[-40:])
sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(4)
report('E1b 启动进入设置页', in_settings(), focus()[:60])
ver = sh('dumpsys package com.kidslock.app | grep versionName').strip()
report('E1c 版本 1.5', 'versionName=1.5' in ver, ver[:40])

ensure_unlocked()

# ============ E2 题库切换（语文·三年级 / 数学·五年级 / 英语·高三）============
def bank_label_shown():
    for t, x, y in dump():
        if '当前题库' in t:
            return t
    return ''

switch_bank('语文', '三'); time.sleep(0.8)
lbl = bank_label_shown()
report('E2a 切换语文·三年级', '语文·三年级' in lbl, lbl)
switch_bank('数学', '五'); time.sleep(0.8)
lbl = bank_label_shown()
report('E2b 切换数学·五年级', '数学·五年级' in lbl, lbl)
switch_bank('英语', '高三'); time.sleep(0.8)
lbl = bank_label_shown()
report('E2c 切换英语·高三', '英语·高三' in lbl, lbl)

# ============ E3 30 秒档计时 → 自动锁屏 ============
ensure_unlocked()
tap_text(exact='30秒'); time.sleep(0.6)
lbl = bank_label_shown()
report('E3a 时长档 30 秒生效', '30 秒' in lbl, lbl)
tap_text(exact='开始计时'); time.sleep(2)
items = dump()
status = next((t for t, x, y in items if '当前状态' in t), '')
report('E3b 计时中状态', '计时中' in status, status)
t0 = time.time()
locked = False
while time.time() - t0 < 60:
    if in_lock():
        locked = True
        break
    time.sleep(3)
report('E3c 30 秒到时自动锁屏', locked, f'{time.time()-t0:.0f}s 后锁屏')
svc = sh('dumpsys activity services com.kidslock.app | grep -c "com.kidslock.app.LockService"')
report('E3d 前台服务运行', int(svc.strip() or 0) >= 1, 'services=' + svc.strip())

# ============ E8 HOME/BACK 拦截（趁当前锁屏）============
key('KEYCODE_HOME', wait=5)
report('E8a HOME 后锁屏回拉', in_lock(), focus()[:60])
key('KEYCODE_BACK', wait=2)
report('E8b BACK 键拦截', in_lock())

# ============ E9 强杀重启状态保持 ============
sh('am force-stop com.kidslock.app'); time.sleep(2)
sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(4)
report('E9 锁屏状态强杀重启后保持（设置页入口被拦截）', in_lock(), focus()[:60])

# ============ E4/E5 切语文库：答错归零 → 连对 3 解锁 ============
if unlock_pin():
    report('E5-pre PIN 解锁进入设置', True)
else:
    # 若 PIN 解锁失败（可能之前测试残留锁定），等待后重试
    time.sleep(31)
    ensure_unlocked()
    report('E5-pre PIN 解锁进入设置', not in_lock())
switch_bank('语文', '三')
tap_text(exact='立即锁屏', swipe_up=True); time.sleep(3)
report('E4-pre 立即锁屏', in_lock())

AMAP = {}
for it in J['banks']['chinese_g3']:
    AMAP[it['q']] = it['opts'][it['ans']]

def current_q(items):
    for t, x, y in items:
        if t in AMAP:
            return t
    return None

# E4 答错归零
items = dump()
q = current_q(items)
wrong_done = False
if q:
    correct = AMAP[q]
    wrong = next(((x, y) for t, x, y in items if t != correct and len(t) <= 30
                  and t not in ('屏幕已锁定', '家长解锁', '语文·三年级')), None)
    if wrong:
        tap(*wrong, wait=2.2)
        items = dump()
        zero = any('已答对 0/3' in t for t, x, y in items)
        report('E4 答错后计数归零并出新题', zero)
        wrong_done = True
if not wrong_done:
    report('E4 答错后计数归零并出新题', False, '未捕获题目')

# E5 连对 3 题解锁
t0 = time.time()
unlocked = False
n_ok = 0
while time.time() - t0 < 120:
    if not in_lock():
        unlocked = True
        break
    items = dump()
    q = current_q(items)
    if not q:
        time.sleep(2)
        continue
    correct = AMAP[q]
    p = find(items, exact=correct)
    if p:
        tap(*p, wait=3.2)
        n_ok += 1
report('E5 连对 3 题自动解锁', unlocked, f'答对 {n_ok} 次')

# ============ E6 解锁题数 5 ============
ensure_unlocked()
tap_text(exact='5题'); time.sleep(0.8)
switch_bank('语文', '三')
tap_text(exact='立即锁屏', swipe_up=True); time.sleep(3)
items = dump()
report('E6 解锁题数切换为 5（进度 0/5）', any('0/5' in t for t, x, y in items),
       next((t for t, x, y in items if '已答对' in t), ''))
# 用 PIN 解锁收尾
unlock_pin()

# ============ E7 PIN 防暴力：错 5 次 → 30 秒锁定 ============
ensure_unlocked()
tap_text(exact='立即锁屏', swipe_up=True); time.sleep(3)
tap_text(exact='家长解锁'); time.sleep(2)
# 输错 5 次（9999）
fails_done = 0
for attempt in range(5):
    digits = {}
    for t, x, y in dump():
        if t in '0123456789':
            digits[t] = (x, y)
    if len(digits) < 10:
        time.sleep(1)
        continue
    for d in '9999':
        tap(*digits[d], wait=0.3)
    time.sleep(1.6)
    fails_done += 1
report('E7a 连错 PIN 5 次仍锁屏', in_lock() and fails_done >= 4, f'完成 {fails_done} 次错误输入')
# 锁定期内输入正确 PIN 应被拒
tap_text(exact='家长解锁'); time.sleep(1.5)
digits = {}
for t, x, y in dump():
    if t in '0123456789':
        digits[t] = (x, y)
if len(digits) >= 10:
    for d in '1234':
        tap(*digits[d], wait=0.3)
    time.sleep(2.5)
    report('E7b 锁定期内正确 PIN 被拒', in_lock())
else:
    report('E7b 锁定期内正确 PIN 被拒', False, 'PIN 键盘未出现')
# 等 31 秒后正确 PIN 解锁
time.sleep(31)
tap_text(exact='家长解锁'); time.sleep(1.5)
ok_pin = False
digits = {}
for t, x, y in dump():
    if t in '0123456789':
        digits[t] = (x, y)
if len(digits) >= 10:
    for d in '1234':
        tap(*digits[d], wait=0.3)
    time.sleep(2.5)
    ok_pin = not in_lock()
report('E7c 锁定期满正确 PIN 解锁', ok_pin)

# ============ E10 设备重启 → 开机自启恢复 ============
ensure_unlocked()
# 先锁屏再重启：验证重启后锁屏状态恢复（BootReceiver 路径）
tap_text(exact='立即锁屏', swipe_up=True); time.sleep(3)
subprocess.run([ADB, '-s', SER, 'reboot'], capture_output=True, timeout=30)
report('E10a 设备重启中', True)
# 等待设备回来
t0 = time.time()
back = False
while time.time() - t0 < 300:
    time.sleep(15)
    r = subprocess.run([ADB, '-s', SER, 'shell', 'echo ok'], capture_output=True, timeout=20)
    if b'ok' in r.stdout:
        # boot 完成？
        bc = subprocess.run([ADB, '-s', SER, 'shell', 'getprop sys.boot_completed'],
                            capture_output=True, timeout=20).stdout.decode().strip()
        if bc == '1':
            back = True
            break
report('E10b 设备重启完成', back, f'{time.time()-t0:.0f}s')
if back:
    time.sleep(10)  # 给 BootReceiver 时间
    locked = in_lock()
    report('E10c 重启后锁屏状态自动恢复', locked, focus()[:70])
    if locked:
        unlock_pin()
        report('E10d 重启后 PIN 可解锁', not in_lock())

# ============ 汇总 ============
print('\n========== E2E 汇总 ==========')
p = sum(1 for _, ok, _ in results if ok)
for n, ok, d in results:
    print(('PASS' if ok else 'FAIL') + ' | ' + n + (' | ' + d if d else ''))
print(f'===== E2E TV: {p} PASS / {len(results)-p} FAIL =====')
sys.exit(0 if p == len(results) else 1)
