#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA TV v3 补测：nav 前强制回顶 + 锁屏遥控交互全项（T2b/T3/T4/T5/T6/T7）"""
import json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qaenv import adb as QADB, SERIAL as SER, TMP as TMP, ROOT as QROOT
ADB = QADB()
QJ = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp', 'apk_questions.json'), encoding='utf-8'))

results = []
def report(name, ok, detail=''):
    results.append((name, ok, detail))
    print(('PASS' if ok else 'FAIL') + f' | {name}' + (f' | {detail}' if detail else ''), flush=True)

def sh(cmd, timeout=40):
    return subprocess.run([ADB, '-s', SER, 'shell', cmd], capture_output=True, timeout=timeout).stdout.decode('utf-8', 'ignore')

def nodes():
    subprocess.run([ADB, '-s', SER, 'shell', 'uiautomator dump /sdcard/ui.xml'], capture_output=True, timeout=40)
    subprocess.run([ADB, '-s', SER, 'pull', '/sdcard/ui.xml', TMP + '/tv4.xml'], capture_output=True, timeout=40)
    try:
        data = open(TMP + '/tv4.xml', encoding='utf-8').read()
    except Exception:
        return []
    return [(m.group(1), (int(m.group(2)) + int(m.group(4))) // 2, (int(m.group(3)) + int(m.group(5))) // 2,
             'focused="true"' in m.group(0), 'clickable="true"' in m.group(0))
            for m in re.finditer(r'<node[^>]*?text="([^"]{0,80})"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*?/>', data)]

def key(k, wait=0.6):
    subprocess.run([ADB, '-s', SER, 'shell', f'input keyevent {k}'], capture_output=True, timeout=30)
    time.sleep(wait)

def focus():
    return sh('dumpsys window | grep mCurrentFocus')

def in_lock():
    return 'LockScreenActivity' in focus()

def top():
    for _ in range(14):
        key('KEYCODE_DPAD_UP', 0.18)

def no_dialog():
    return not any('家长PIN码' in n[0] for n in nodes())

def nav_to(txt, steps=35):
    """先回顶再坐标引导（顶部按钮场景）；目标在下方时逐步 DOWN"""
    top()
    for _ in range(steps):
        ns = nodes()
        tgt = next((n for n in ns if n[0] == txt and n[4]), None)
        if not tgt:
            return False
        foc = next((n for n in ns if n[3]), None)
        if foc is None:
            key('KEYCODE_DPAD_UP', 0.4)
            continue
        if foc[0] == txt:
            return True
        dy, dx = tgt[2] - foc[2], tgt[1] - foc[1]
        if abs(dy) > 30:
            key('KEYCODE_DPAD_DOWN' if dy > 0 else 'KEYCODE_DPAD_UP', 0.3)
        elif abs(dx) > 30:
            key('KEYCODE_DPAD_RIGHT' if dx > 0 else 'KEYCODE_DPAD_LEFT', 0.3)
        else:
            return True
    return False

def lock_by_remote():
    for attempt in range(3):
        if not no_dialog():
            key('KEYCODE_BACK', 1.5)  # 关可能的对话框
        if nav_to('立即锁屏'):
            key('KEYCODE_DPAD_CENTER', 3.0)
            if in_lock():
                return True
    return False

# ===== 准备：解锁到设置页 =====
sh('input keyevent KEYCODE_WAKEUP')
sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(2.5)
if in_lock():
    # D-pad PIN 解锁
    ok = nav_to('家长解锁')
    if ok:
        key('KEYCODE_DPAD_CENTER', 1.8)
        for d in '1234':
            if nav_to(d):
                key('KEYCODE_DPAD_CENTER', 0.45)
        time.sleep(2.5)
    sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(2)
report('P0 遥控解锁就绪', not in_lock() and no_dialog())

# ===== T2b 遥控锁屏（回顶版）=====
ok2b = lock_by_remote()
report('T2b 遥控「立即锁屏」+ 确认键锁屏', ok2b, focus()[:50])

if ok2b:
    # ===== T3 锁屏遥控答题 =====
    AMAPS = {}
    for bid, arr in QJ['banks'].items():
        for it in arr:
            AMAPS.setdefault(it['q'], it['opts'][it['ans']])

    def remote_answer(expect_correct=True):
        """遥控答当前题：找题目→导航到(正确/错误)选项→CENTER"""
        ns = nodes()
        q = next((n[0] for n in ns if n[0] in AMAPS), None)
        if q is None:
            return False
        correct = AMAPS[q]
        want = correct if expect_correct else next(
            (n[0] for n in ns if n[4] and n[0] != correct and n[0] != '家长解锁'
             and len(n[0]) <= 40 and '已答对' not in n[0]), None)
        if want is None:
            return False
        ok = nav_to(want, 25)
        key('KEYCODE_DPAD_CENTER', 3.0)
        return ok

    # T3a 答错
    did = remote_answer(expect_correct=False)
    prog = [n[0] for n in nodes() if '已答对' in n[0]]
    report('T3a 遥控答错归零出新题', did and any(re.search(r'已答对 0/\d', t) for t in prog), str(prog))

    # T3b 连对解锁
    t0 = time.time(); unlocked = False; n_try = 0
    while time.time() - t0 < 330:
        if not in_lock():
            unlocked = True; break
        if remote_answer(expect_correct=True):
            n_try += 1
            if n_try >= 25:
                break
        else:
            time.sleep(1.2)
    report('T3b 遥控连对 N 题自动解锁', unlocked, f'遥控作答 {n_try} 次')

    # ===== T4 悬浮窗遥控拦截（需再锁）=====
    if not in_lock():
        sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(2)
    ok4 = lock_by_remote()
    report('T4-pre 遥控再锁屏', ok4)
    if ok4:
        key('KEYCODE_HOME', 6)
        key('KEYCODE_DPAD_CENTER', 3.5)
        report('T4a HOME 后确认键回锁屏', in_lock(), focus()[:50])
        key('KEYCODE_ENTER', 3.5)
        report('T4b ENTER 键回锁屏', in_lock())
        # ===== T5 BACK =====
        key('KEYCODE_BACK', 2)
        report('T5 锁屏页 BACK 无效', in_lock())
        # ===== T6 杂项按键 =====
        for k in ('KEYCODE_MENU', 'KEYCODE_VOLUME_UP', 'KEYCODE_VOLUME_DOWN', 'KEYCODE_0', 'KEYCODE_PROG_RED'):
            key(k, 0.4)
        report('T6 杂项按键不崩溃', sh('pidof com.kidslock.app').strip() != '' and in_lock())
        # ===== T7 HOME 回拉 =====
        key('KEYCODE_HOME', 6)
        report('T7 HOME 回拉锁屏', in_lock(), focus()[:50])
        # ===== 收尾 D-pad PIN 解锁 =====
        okf = nav_to('家长解锁')
        if okf:
            key('KEYCODE_DPAD_CENTER', 1.8)
            for d in '1234':
                nav_to(d)
                key('KEYCODE_DPAD_CENTER', 0.45)
            time.sleep(2.5)
        report('收尾 遥控全键盘 PIN 解锁', not in_lock())

print('\n========== TV 遥控 v3 补测汇总 ==========')
p = sum(1 for _, ok, _ in results if ok)
for n, ok, d in results:
    print(('PASS' if ok else 'FAIL') + ' | ' + n + (' | ' + d if d else ''))
print(f'===== TV 遥控 v3: {p} PASS / {len(results) - p} FAIL =====')
sys.exit(0 if p == len(results) else 1)
