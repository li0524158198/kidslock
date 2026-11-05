#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA 最终靶向：E2 切库（顶部断言）+ E4/E5 答题（先确认库再锁）"""
import json, re, subprocess, time

from qaenv import adb, SERIAL as SER, TMP, load_questions
ADB = adb()
J = load_questions()

def sh(cmd, timeout=40):
    return subprocess.run([ADB, '-s', SER, 'shell', cmd], capture_output=True, timeout=timeout).stdout.decode('utf-8', 'ignore')

def dump():
    subprocess.run([ADB, '-s', SER, 'shell', 'uiautomator dump /sdcard/ui.xml'], capture_output=True, timeout=40)
    subprocess.run([ADB, '-s', SER, 'pull', '/sdcard/ui.xml', TMP + '/v4.xml'], capture_output=True, timeout=40)
    try:
        data = open(TMP + '/v4.xml', encoding='utf-8').read()
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

def scroll_top():
    for _ in range(5):
        if any(t == '儿童锁屏设置' for t, x, y in dump()):
            return
        swipe(640, 200, 640, 600)

def bank_label():
    scroll_top()
    for t, x, y in dump():
        if t.startswith('当前题库：'):
            return t
    return ''

def find_tap(exact, progressive=False):
    if progressive:
        scroll_top()
    for _ in range(6):
        for t, x, y in dump():
            if t == exact:
                tap(x, y)
                return True
        if not progressive:
            return False
        swipe(640, 550, 640, 250)
    return False

sh('input keyevent KEYCODE_WAKEUP')
sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(3)
if in_lock():
    find_tap('家长解锁'); time.sleep(1.5)
    d = {}
    for t, x, y in dump():
        if t in '0123456789':
            d[t] = (x, y)
    for c in '1234':
        if c in d:
            tap(*d[c], wait=0.35)
    time.sleep(2.5)
    sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(2)

# E2：切库后回顶断言
for sub, grade, expect in [('语文', '三', '语文·三年级'), ('数学', '五', '数学·五年级'), ('英语', '高三', '英语·高三')]:
    find_tap(sub, progressive=True); time.sleep(0.8)
    find_tap(grade, progressive=True); time.sleep(1.2)
    lbl = bank_label()
    print(('PASS' if expect in lbl else 'FAIL') + f' | E2 切换{expect} | {lbl}')

# E4/E5：切到语文·三并确认，再锁屏答题
find_tap('语文', progressive=True); time.sleep(0.8)
find_tap('三', progressive=True); time.sleep(1.2)
lbl = bank_label()
print(('PASS' if '语文·三年级' in lbl else 'FAIL') + f' | E4-pre 切到语文·三年级 | {lbl}')

AMAP = {}
for it in J['banks']['chinese_g3']:
    AMAP[it['q']] = it['opts'][it['ans']]

def current_q(items):
    for t, x, y in items:
        if t in AMAP:
            return t
    return None

find_tap('立即锁屏', progressive=True); time.sleep(3)
print(('PASS' if in_lock() else 'FAIL') + ' | E4-pre2 立即锁屏')
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
        print('FAIL | E4 答错归零出新题 | 无干扰项')
else:
    bank_shown = next((t for t, x, y in items if '·' in t and len(t) < 12), '')
    print(f'FAIL | E4 答错归零出新题 | q={q} locked={in_lock()} 锁屏显示库={bank_shown}')

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
print('===== 最终靶向结束 =====')
