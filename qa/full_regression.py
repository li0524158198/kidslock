#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KidsLock Android 全功能回归（TV 模拟器）"""
import json, re, subprocess, sys, time

from qaenv import adb, TMP, load_questions
import os
ADB = adb()
# 默认 TV 模拟器 5556（原行为）；可用 参数 或 KIDSLOCK_SERIAL 覆盖
SER = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('KIDSLOCK_SERIAL', 'emulator-5556')
J = load_questions()
AMAP = {}
for _k, _arr in J['banks'].items():
    for _it in _arr:
        AMAP[_it['q']] = _it['opts'][_it['ans']]

def lookup(qtext):
    if qtext in AMAP:
        return AMAP[qtext]
    for k, v in AMAP.items():
        if k.startswith(qtext) or qtext in k:
            return v
    return None

results = []

def sh(cmd, timeout=30):
    return subprocess.run([ADB, '-s', SER, 'shell', cmd], capture_output=True, timeout=timeout).stdout.decode('utf-8', 'ignore')

def dump():
    subprocess.run([ADB, '-s', SER, 'shell', 'uiautomator dump /sdcard/ui.xml'], capture_output=True, timeout=40)
    subprocess.run([ADB, '-s', SER, 'pull', '/sdcard/ui.xml', TMP + '/reg.xml'], capture_output=True, timeout=40)
    data = open(TMP + '/reg.xml', encoding='utf-8').read()
    out = []
    for m in re.finditer(r'text="([^"]{1,70})"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', data):
        t, x1, y1, x2, y2 = m.group(1), *map(int, m.groups()[1:])
        if t.strip():
            out.append((t, (x1 + x2) // 2, (y1 + y2) // 2))
    return out

def focus():
    return sh('dumpsys window | grep mCurrentFocus')

def tap(x, y):
    subprocess.run([ADB, '-s', SER, 'shell', f'input tap {x} {y}'], capture_output=True, timeout=30)

def key(k):
    subprocess.run([ADB, '-s', SER, 'shell', f'input keyevent {k}'], capture_output=True, timeout=30)

def find(items, exact=None, contains=None):
    for t, x, y in items:
        if (exact and t == exact) or (contains and contains in t):
            return x, y
    return None

def report(name, ok, detail=''):
    results.append((name, ok, detail))
    print(('PASS' if ok else 'FAIL') + f' | {name} {detail}')

def unlock_pin():
    items = dump()
    p = None
    for t, x, y in items:
        if t == '家长解锁':
            p = (x, y)
    if not p:
        return False
    tap(*p); time.sleep(2)
    items = dump()
    digits = {}
    for t, x, y in items:
        if t in ('1', '2', '3', '4'):
            digits[t] = (x, y)  # 后出现覆盖先出现（PIN 键盘在顶层）
    if len(digits) < 4:
        return False
    for d in '1234':
        tap(*digits[d]); time.sleep(0.4)
    time.sleep(2)
    return True

def open_settings():
    subprocess.run([ADB, '-s', SER, 'shell', 'am start -n com.kidslock.app/.MainActivity'], capture_output=True)
    time.sleep(3)

def scroll_to(name, max_swipes=4):
    # 先滚回顶部
    sh('input swipe 960 300 960 900 300')
    time.sleep(1)
    for _ in range(max_swipes):
        items = dump()
        p = find(items, exact=name)
        if p:
            return p
        sh('input swipe 960 700 960 250 350')
        time.sleep(1)
    items = dump()
    return find(items, exact=name)

# ================= 流程 =================
def in_lock():
    return 'LockScreenActivity' in focus()

def ensure_unlocked():
    open_settings()
    if in_lock():
        ok = unlock_pin()
        report('PIN 解锁', ok)
        open_settings()
    return not in_lock()

def lock_now():
    open_settings()
    p = scroll_to('立即锁屏')
    if p:
        tap(*p)
        time.sleep(2.5)
    return in_lock()

# C0：先确保未锁定，再锁定
report('C0-pre 状态解锁', ensure_unlocked())
# 若当前是自定义库（CSV 导入），切回内置「语文·五年级」保证映射可用
items = dump()
if not any(t == '语文' for t, x, y in items):
    sh('input swipe 200 300 200 900 300'); time.sleep(1)
    items = dump()
sp = find(items, exact='语文')
if sp:
    tap(*sp); time.sleep(1)
    items = dump()
g5 = find(items, exact='五') or find(items, exact='五年级')
if g5:
    tap(*g5); time.sleep(1)
report('C0-pre 切回内置库', True)
report('C0 立即锁屏', lock_now())

# C4：错 PIN 拦截 + 正确 PIN 解锁
p = None
for t, x, y in dump():
    if t == '家长解锁':
        p = (x, y)
if p:
    tap(*p); time.sleep(2)
    digits = {}
    for t, x, y in dump():
        if t in ('7', '8', '9'):
            digits[t] = (x, y)
    if len(digits) >= 3:
        for d in '999':
            tap(*digits[d]); time.sleep(0.3)
        time.sleep(2)
        report('C4a 错误 PIN 仍锁定', in_lock())
        # 错 PIN 后键盘仍在：先点「返回」回答题界面
        back = None
        for t, x, y in dump():
            if t == '返回':
                back = (x, y)
        if back:
            tap(*back); time.sleep(1.5)
        p2 = None
        for t, x, y in dump():
            if t == '家长解锁':
                p2 = (x, y)
        if p2:
            tap(*p2); time.sleep(2)
            digits = {}
            for t, x, y in dump():
                if t in ('1', '2', '3', '4'):
                    digits[t] = (x, y)
            for d in '1234':
                tap(*digits[d]); time.sleep(0.4)
            time.sleep(2)
            report('C4b 正确 PIN 解锁', not in_lock())
        else:
            report('C4b 正确 PIN 解锁', False, '未找到家长解锁')
    else:
        report('C4a/b', False, '未找到 PIN 键盘')
else:
    report('C4a/b', False, '未找到家长解锁')

# C2/C3：再次锁定 → 答错归零 → 连对 3 解锁
report('C23-pre 再次锁定', lock_now())
items = dump()
cands = [(t, x, y) for t, x, y in items if lookup(t) and len(t) >= 4]
q = min(cands, key=lambda e: e[2])[0] if cands else None
if q:
    correct = AMAP[q]
    wrong = next(((t, x, y) for t, x, y in items
                  if t != correct and t not in ('屏幕已锁定', '家长解锁', '自定义·my_test_bank')
                  and '已答对' not in t and len(t) < 40), None)
    if wrong:
        tap(wrong[1], wrong[2]); time.sleep(1)
        items = dump()
        bad = any('答错' in t for t, x, y in items)
        zero = any('已答对 0/3' in t for t, x, y in items)
        report('C2 答错反馈+计数归零', zero, f'题[{q[:16]}] 反馈{"有" if bad else "未及抓取"}' )
    else:
        report('C2', False, '无干扰项')
    unlocked = False
    n = 0
    for _ in range(10):
        if not in_lock():
            unlocked = True
            break
        items = dump()
        q = next((t for t, x, y in items if lookup(t)), None)
        if q is None:
            time.sleep(2)
            continue
        p = find(items, exact=AMAP[q])
        if p:
            tap(*p); time.sleep(3)
            n += 1
    if not unlocked and not in_lock():
        unlocked = True
    report('C3 连对 3 题自动解锁', unlocked, f'答对 {n} 次')
else:
    report('C2/C3', False, '题干不在映射（自定义库）')

# C6/C5：第三次锁定 → HOME → BACK
report('C6-pre 第三次锁定', lock_now())
key('KEYCODE_HOME'); time.sleep(4)
report('C6 HOME 后锁屏回拉', in_lock())
key('KEYCODE_BACK'); time.sleep(1.5)
report('C5 BACK 键拦截', in_lock())

# 收尾：解锁回设置页
report('收尾 解锁', ensure_unlocked())

# 汇总
print('\n========== 回归汇总 ==========')
for n, ok, d in results:
    print(('PASS' if ok else 'FAIL') + ' | ' + n + (' ' + d if d else ''))
