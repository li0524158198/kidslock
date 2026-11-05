#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA E v3: 滚动策略修正版（先回顶再渐进下移；状态行精确断言）"""
import json, re, subprocess, sys, time

from qaenv import adb, SERIAL as SER, TMP, load_questions
ADB = adb()
J = load_questions()

results = []
def report(name, ok, detail=''):
    results.append((name, ok, detail))
    print(('PASS' if ok else 'FAIL') + f' | {name}' + (f' | {detail}' if detail else ''), flush=True)

def sh(cmd, timeout=40):
    return subprocess.run([ADB, '-s', SER, 'shell', cmd], capture_output=True, timeout=timeout).stdout.decode('utf-8', 'ignore')

def dump():
    subprocess.run([ADB, '-s', SER, 'shell', 'uiautomator dump /sdcard/ui.xml'], capture_output=True, timeout=40)
    subprocess.run([ADB, '-s', SER, 'pull', '/sdcard/ui.xml', TMP + '/e2e3.xml'], capture_output=True, timeout=40)
    try:
        data = open(TMP + '/e2e3.xml', encoding='utf-8').read()
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

def swipe(x1, y1, x2, y2, ms=300):
    subprocess.run([ADB, '-s', SER, 'shell', f'input swipe {x1} {y1} {x2} {y2} {ms}'], capture_output=True, timeout=30)
    time.sleep(1.0)

def focus():
    return sh('dumpsys window | grep mCurrentFocus')

def in_lock():
    return 'LockScreenActivity' in focus()

def service_running():
    out = sh('dumpsys activity services com.kidslock.app')
    return 'ServiceRecord' in out and 'LockService' in out

def find(items, exact=None, contains=None):
    for t, x, y in items:
        if (exact and t == exact) or (contains and contains in t):
            return x, y
    return None

def scroll_top():
    for _ in range(5):
        items = dump()
        if find(items, exact='儿童锁屏设置'):  # 顶部标题可见
            return True
        swipe(640, 200, 640, 600)
    return find(dump(), exact='儿童锁屏设置') is not None

def tap_text(exact=None, contains=None):
    """先回顶，向下渐进扫描"""
    scroll_top()
    for _ in range(6):
        items = dump()
        p = find(items, exact=exact, contains=contains)
        if p:
            tap(*p)
            return True
        swipe(640, 550, 640, 250)  # 向下翻一屏
    return False

def status_text():
    """精确取状态行（带全角冒号），排除按钮"""
    for t, x, y in dump():
        if t.startswith('当前题库：') or t.startswith('当前状态：'):
            return t
    return ''

def unlock_pin():
    if not tap_text(exact='家长解锁'):
        return False
    time.sleep(1.5)
    digits = {}
    for t, x, y in dump():
        if t in '0123456789':
            digits[t] = (x, y)
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

def switch_bank(subject, grade):
    ok1 = tap_text(exact=subject)
    time.sleep(0.6)
    ok2 = tap_text(exact=grade)
    time.sleep(1.2)
    return ok1 and ok2

# ===== E1 =====
sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(3)
f1 = focus()
report('E1 启动正常', ('LockScreenActivity' in f1) or ('MainActivity' in f1), f1[:60])
ensure_unlocked()

# ===== E2 题库切换 =====
for sub, grade, expect in [('语文', '三', '语文·三年级'), ('数学', '五', '数学·五年级'), ('英语', '高三', '英语·高三')]:
    ok = switch_bank(sub, grade)
    lbl = status_text()
    report(f'E2 切换{expect}', ok and expect in lbl, lbl)

# ===== E3 30 秒档 → 自动锁屏 =====
ensure_unlocked()
ok30 = tap_text(exact='30秒')
lbl = status_text()
report('E3a 时长档 30 秒生效', ok30 and '30 秒' in lbl, lbl)
ok_start = tap_text(exact='开始计时')
time.sleep(2.5)
svc = service_running()
report('E3b 服务运行', ok_start and svc, f'点击开始计时={ok_start} svc={svc}')
t0 = time.time()
locked = False
while time.time() - t0 < 75:
    if in_lock():
        locked = True
        break
    time.sleep(3)
report('E3c 30 秒到时自动锁屏', locked, f'{time.time() - t0:.0f}s')

if locked:
    # ===== E8 HOME/BACK =====
    key('KEYCODE_HOME', wait=6)
    report('E8a HOME 后锁屏回拉', in_lock(), focus()[:60])
    key('KEYCODE_BACK', wait=2)
    report('E8b BACK 拦截', in_lock())
    # ===== E9 =====
    sh('am force-stop com.kidslock.app'); time.sleep(2)
    sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(4)
    report('E9 锁屏状态强杀后保持', in_lock(), focus()[:60])

    # ===== E4 答错归零 =====
    unlock_pin()
    switch_bank('语文', '三')
    ok_lock = tap_text(exact='立即锁屏')
    time.sleep(3)
    AMAP = {}
    for it in J['banks']['chinese_g3']:
        AMAP[it['q']] = it['opts'][it['ans']]

    def current_q(items):
        for t, x, y in items:
            if t in AMAP:
                return t
        return None

    report('E4-pre 立即锁屏成功', in_lock())
    items = dump()
    q = current_q(items)
    done_e4 = False
    if q:
        correct = AMAP[q]
        wrong = next(((x, y) for t, x, y in items if t != correct and len(t) <= 40
                      and t not in ('屏幕已锁定', '家长解锁', '语文·三年级') and '已答对' not in t), None)
        if wrong:
            tap(*wrong, wait=2.5)
            items = dump()
            zero = any('已答对 0/3' in t for t, x, y in items)
            report('E4 答错归零出新题', zero)
            done_e4 = True
    if not done_e4:
        report('E4 答错归零出新题', False, f'q={q}')

    # ===== E5 连对 3 解锁 =====
    t0 = time.time()
    unlocked = False
    n_ok = 0
    while time.time() - t0 < 150:
        if not in_lock():
            unlocked = True
            break
        items = dump()
        q = current_q(items)
        if not q:
            time.sleep(2)
            continue
        p = find(items, exact=AMAP[q])
        if p:
            tap(*p, wait=3.5)
            n_ok += 1
    report('E5 连对 3 题自动解锁', unlocked, f'答对 {n_ok} 次')

    # ===== E6 =====
    ensure_unlocked()
    tap_text(exact='5题'); time.sleep(0.8)
    switch_bank('语文', '三')
    tap_text(exact='立即锁屏'); time.sleep(3)
    items = dump()
    prog = next((t for t, x, y in items if '已答对' in t), '')
    report('E6 解锁题数 5（进度 0/5）', '0/5' in prog, prog)
    unlock_pin()

    # ===== E7 PIN =====
    ensure_unlocked()
    tap_text(exact='立即锁屏'); time.sleep(3)
    tap_text(exact='家长解锁'); time.sleep(2)
    fails_done = 0
    for attempt in range(5):
        digits = {}
        for t, x, y in dump():
            if t in '0123456789':
                digits[t] = (x, y)
        if len(digits) < 10:
            time.sleep(1.5)
            continue
        for d in '9999':
            tap(*digits[d], wait=0.3)
        time.sleep(1.8)
        fails_done += 1
    report('E7a 连错 PIN×5 后仍锁屏', in_lock() and fails_done >= 4, f'{fails_done} 轮')

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

    time.sleep(31)
    tap_text(exact='家长解锁'); time.sleep(1.5)
    digits = {}
    for t, x, y in dump():
        if t in '0123456789':
            digits[t] = (x, y)
    ok_pin = False
    if len(digits) >= 10:
        for d in '1234':
            tap(*digits[d], wait=0.3)
        time.sleep(2.5)
        ok_pin = not in_lock()
    report('E7c 锁定期满正确 PIN 解锁', ok_pin)

print('\n========== E2E v3 汇总 ==========')
p = sum(1 for _, ok, _ in results if ok)
for n, ok, d in results:
    print(('PASS' if ok else 'FAIL') + ' | ' + n + (' | ' + d if d else ''))
print(f'===== E2E v3: {p} PASS / {len(results) - p} FAIL =====')
sys.exit(0 if p == len(results) else 1)
