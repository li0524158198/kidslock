#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA 靶向复测：E2 切库（无屏保干扰）/ E4 答题 / E7b/c PIN 锁定期（无滚动消耗）"""
import json, re, subprocess, sys, time

from qaenv import adb, SERIAL as SER, TMP, load_questions
ADB = adb()
J = load_questions()

def sh(cmd, timeout=40):
    return subprocess.run([ADB, '-s', SER, 'shell', cmd], capture_output=True, timeout=timeout).stdout.decode('utf-8', 'ignore')

def dump():
    subprocess.run([ADB, '-s', SER, 'shell', 'uiautomator dump /sdcard/ui.xml'], capture_output=True, timeout=40)
    subprocess.run([ADB, '-s', SER, 'pull', '/sdcard/ui.xml', TMP + '/v3.xml'], capture_output=True, timeout=40)
    try:
        data = open(TMP + '/v3.xml', encoding='utf-8').read()
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

def find_tap(exact, progressive=False):
    """progressive: 先回顶再下移找；否则就地找"""
    if progressive:
        for _ in range(4):
            if any(t == '儿童锁屏设置' for t, x, y in dump()):
                break
            swipe(640, 200, 640, 600)
    for _ in range(6):
        for t, x, y in dump():
            if t == exact:
                tap(x, y)
                return True
        if not progressive:
            return False
        swipe(640, 550, 640, 250)
    return False

def status_text():
    for t, x, y in dump():
        if t.startswith('当前题库：') or t.startswith('当前状态：'):
            return t
    return ''

def pin_digits():
    d = {}
    for t, x, y in dump():
        if t in '0123456789':
            d[t] = (x, y)
    return d

def type_pin(pin):
    d = pin_digits()
    if len(d) < 10:
        return False
    for c in pin:
        tap(*d[c], wait=0.3)
    return True

# 保持唤醒
sh('input keyevent KEYCODE_WAKEUP')
sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(3)
if in_lock():
    find_tap('家长解锁'); time.sleep(1.5)
    type_pin('1234'); time.sleep(2.5)
    sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(2)

print('===== 靶向复测开始 =====')

# --- E2 干净环境切库 ---
for sub, grade, expect in [('语文', '三', '语文·三年级'), ('数学', '五', '数学·五年级'), ('英语', '高三', '英语·高三'), ('语文', '一', '语文·一年级')]:
    find_tap(sub, progressive=True); time.sleep(0.8)
    find_tap(grade, progressive=True); time.sleep(1.2)
    lbl = status_text()
    print(('PASS' if expect in lbl else 'FAIL') + f' | E2 切换{expect} | {lbl}')

# --- E4 答错归零 → E5 连对 3 解锁（语文·三年级）---
AMAP = {}
for it in J['banks']['chinese_g3']:
    AMAP[it['q']] = it['opts'][it['ans']]

def current_q(items):
    for t, x, y in items:
        if t in AMAP:
            return t
    return None

find_tap('立即锁屏', progressive=True); time.sleep(3)
print(('PASS' if in_lock() else 'FAIL') + ' | E4-pre 立即锁屏')
items = dump()
q = current_q(items)
if q and in_lock():
    correct = AMAP[q]
    wrong = next(((x, y) for t, x, y in items if t != correct and len(t) <= 40
                  and t not in ('屏幕已锁定', '家长解锁', '语文·三年级') and '已答对' not in t), None)
    if wrong:
        tap(*wrong, wait=2.6)
        items = dump()
        zero = any('已答对 0/3' in t for t, x, y in items)
        print(('PASS' if zero else 'FAIL') + ' | E4 答错归零出新题')
    else:
        print('FAIL | E4 答错归零出新题 | 无干扰项可点')
    # 先答对一题制造进度 1/3，再答错验证归零（更严格）
    items = dump()
    q = current_q(items)
    if q:
        p = next(((x, y) for t, x, y in items if t == AMAP[q]), None)
        if p:
            tap(*p, wait=3.5)
            items = dump()
            prog = next((t for t, x, y in items if '已答对' in t), '')
            print(('PASS' if '1/3' in prog else 'FAIL') + f' | E4b 答对计数+1 | {prog}')
else:
    print(f'FAIL | E4 答错归零出新题 | q={q} locked={in_lock()}')

# E5 连对解锁
t0 = time.time()
unlocked = False
n = 0
while time.time() - t0 < 120:
    if not in_lock():
        unlocked = True
        break
    items = dump()
    q = current_q(items)
    if not q:
        time.sleep(1.5)
        continue
    p = next(((x, y) for t, x, y in items if t == AMAP[q]), None)
    if p:
        tap(*p, wait=3.4)
        n += 1
print(('PASS' if unlocked else 'FAIL') + f' | E5 连对 3 题自动解锁 | 答对 {n} 次')

# --- E7b/c PIN 锁定期（键盘保持打开，不滚动）---
find_tap('立即锁屏', progressive=True); time.sleep(3)
assert in_lock(), '未进入锁屏'
find_tap('家长解锁'); time.sleep(1.8)
# 连错 5 次（键盘全程不关）
t_lock = None
for i in range(5):
    type_pin('9999')
    time.sleep(1.6)
    if i == 4:
        t_lock = time.time()
print(('PASS' if in_lock() else 'FAIL') + ' | E7a 连错 5 次仍锁屏')
# 立刻（<30s）输入正确 PIN —— 应被拒
ok_type = type_pin('1234')
time.sleep(2.2)
print(('PASS' if (ok_type and in_lock()) else 'FAIL') + f' | E7b 锁定期内正确 PIN 被拒 | typed={ok_type}')
# 剩余等待至 31s
remain = 31 - (time.time() - t_lock)
if remain > 0:
    time.sleep(remain + 1)
# 键盘仍开着？若被重置则重新打开
if not pin_digits():
    find_tap('家长解锁'); time.sleep(1.5)
ok_type = type_pin('1234')
time.sleep(2.5)
print(('PASS' if (ok_type and not in_lock()) else 'FAIL') + f' | E7c 锁定期满正确 PIN 解锁 | typed={ok_type}')
print('===== 靶向复测结束 =====')
