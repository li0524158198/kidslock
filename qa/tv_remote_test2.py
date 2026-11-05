#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA TV v2: 遥控器（D-pad）专项——全程按键驱动，PIN 解锁走屏上键盘导航（app 不响应物理数字键）"""
import json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qaenv import adb as QADB, SERIAL as SER, TMP as TMP, ROOT as QROOT
ADB = QADB()
APK = str(QROOT / 'dist' / 'kidslock-release-universal.apk')
QJ = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp', 'apk_questions.json'), encoding='utf-8'))

results = []
def report(name, ok, detail=''):
    results.append((name, ok, detail))
    print(('PASS' if ok else 'FAIL') + f' | {name}' + (f' | {detail}' if detail else ''), flush=True)

def sh(cmd, timeout=40):
    return subprocess.run([ADB, '-s', SER, 'shell', cmd], capture_output=True, timeout=timeout).stdout.decode('utf-8', 'ignore')

def dump_nodes():
    subprocess.run([ADB, '-s', SER, 'shell', 'uiautomator dump /sdcard/ui.xml'], capture_output=True, timeout=40)
    subprocess.run([ADB, '-s', SER, 'pull', '/sdcard/ui.xml', TMP + '/tv2.xml'], capture_output=True, timeout=40)
    try:
        data = open(TMP + '/tv2.xml', encoding='utf-8').read()
    except Exception:
        return []
    out = []
    for m in re.finditer(r'<node[^>]*?text="([^"]{0,80})"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*?/>', data):
        t = m.group(1)
        x1, y1, x2, y2 = map(int, m.groups()[1:])
        seg = m.group(0)
        out.append({'text': t, 'x': (x1 + x2) // 2, 'y': (y1 + y2) // 2,
                    'focused': 'focused="true"' in seg, 'clickable': 'clickable="true"' in seg})
    return out

def key(k, wait=0.6):
    subprocess.run([ADB, '-s', SER, 'shell', f'input keyevent {k}'], capture_output=True, timeout=30)
    time.sleep(wait)

def focus():
    return sh('dumpsys window | grep mCurrentFocus')

def in_lock():
    return 'LockScreenActivity' in focus()

def in_settings():
    return 'MainActivity' in focus()

def nav_to(target_text, max_steps=30):
    """坐标引导 D-pad 导航：把焦点移到指定文字的可点击节点，成功返回 True"""
    for attempt in range(2):
        nodes = dump_nodes()
        target = next((n for n in nodes if n['text'] == target_text and n['clickable']), None)
        if not target:
            return False
        for _ in range(max_steps):
            nodes = dump_nodes()
            foc = next((n for n in nodes if n['focused'] and n['clickable']), None)
            if foc is None:
                key('KEYCODE_DPAD_UP', 0.4)
                continue
            if foc['text'] == target_text:
                return True
            dy, dx = target['y'] - foc['y'], target['x'] - foc['x']
            if abs(dy) > 30:
                key('KEYCODE_DPAD_DOWN' if dy > 0 else 'KEYCODE_DPAD_UP', 0.3)
            elif abs(dx) > 30:
                key('KEYCODE_DPAD_RIGHT' if dx > 0 else 'KEYCODE_DPAD_LEFT', 0.3)
            else:
                return True
    return False

def pin_unlock_dpad():
    """纯 D-pad 的 PIN 解锁：家长解锁 → 逐位导航数字键盘 → 确认"""
    if not in_lock():
        return True
    if not nav_to('家长解锁'):
        return False
    key('KEYCODE_DPAD_CENTER', 1.8)
    for d in '1234':
        if nav_to(d):
            key('KEYCODE_DPAD_CENTER', 0.45)
        else:
            return False
    time.sleep(2.5)
    return not in_lock()

# ============ T1 Leanback 入口 ============
sh('settings put secure screensaver_enabled 0')
subprocess.run([ADB, '-s', SER, 'install', '-r', APK], capture_output=True, timeout=120)
subprocess.run([ADB, '-s', SER, 'shell',
                'am start -a android.intent.action.MAIN -c android.intent.category.LEANBACK_LAUNCHER -n com.kidslock.app/.MainActivity'],
               capture_output=True, timeout=30)
time.sleep(3)
report('T1 Leanback 启动器入口', 'com.kidslock.app' in focus(), focus()[:55])

# 解锁到设置页（D-pad 路径，最多 3 轮）
ok_unl = False
for _ in range(3):
    if not in_lock():
        ok_unl = True
        break
    ok_unl = pin_unlock_dpad()
    if ok_unl:
        break
    # 键盘可能还开着：按 BACK 回答题界面再试
    key('KEYCODE_BACK', 1.5)
if not in_settings():
    sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(2.5)
report('T1b 遥控 D-pad 完成 PIN 解锁进入设置', in_settings() and not in_lock())

# ============ T2 设置页 D-pad 导航 ============
for _ in range(15):
    key('KEYCODE_DPAD_UP', 0.2)
visited, prev, stuck = [], None, 0
for i in range(45):
    nodes = dump_nodes()
    t = next((n['text'] for n in nodes if n['focused'] and n['text'].strip()), None)
    if t is not None and t != prev:
        visited.append(t)
    stuck = stuck + 1 if (t == prev and t is not None) else 0
    prev = t
    if stuck >= 6:
        break
    key('KEYCODE_DPAD_DOWN', 0.3)
report('T2a 设置页 D-pad 焦点可遍历（≥8 站）', len(visited) >= 8,
       f'{len(visited)} 站: {" > ".join(visited[:12])}')

ok_nav = nav_to('立即锁屏')
if ok_nav:
    key('KEYCODE_DPAD_CENTER', 3.0)
report('T2b 遥控选中「立即锁屏」+ 确认进入锁屏', ok_nav and in_lock(), focus()[:50])

# ============ T3 锁屏遥控答题 ============
AMAPS = {}
for bid in ('chinese_g1', 'chinese_g2', 'chinese_g3'):
    AMAPS.update({it['q']: it['opts'][it['ans']] for it in QJ['banks'][bid]})

def remote_answer_once():
    """D-pad 答当前题：返回 (处理了题目, 是否可能答对)"""
    nodes = dump_nodes()
    q = next((n['text'] for n in nodes if n['text'] in AMAPS), None)
    if q is None:
        return False, False
    correct = AMAPS[q]
    ok = nav_to(correct, 25)
    key('KEYCODE_DPAD_CENTER', 3.0)
    return True, ok

if in_lock():
    # T3a 答错：导航到干扰项
    nodes = dump_nodes()
    q = next((n['text'] for n in nodes if n['text'] in AMAPS), None)
    done3a = False
    if q:
        correct = AMAPS[q]
        cand = [n for n in nodes if n['clickable'] and n['text'] != correct and n['text'] != '家长解锁'
                and len(n['text']) <= 40 and '已答对' not in n['text']]
        if cand and nav_to(cand[0]['text'], 25):
            key('KEYCODE_DPAD_CENTER', 3.0)
            prog = [n['text'] for n in dump_nodes() if '已答对' in n['text']]
            done3a = any(re.search(r'已答对 0/\d', t) for t in prog)
            report('T3a 遥控答错归零出新题', done3a, str(prog))
    if not done3a:
        report('T3a 遥控答错归零出新题', False, f'q={q}')

    t0 = time.time(); unlocked = False; n_ok = 0; n_try = 0
    while time.time() - t0 < 300:
        if not in_lock():
            unlocked = True; break
        did, _ = remote_answer_once()
        if did:
            n_try += 1
        else:
            time.sleep(1.2)
        if n_try > 30:
            break
    report('T3b 遥控器连对 N 题自动解锁', unlocked, f'遥控作答 {n_try} 次')

# ============ T4 悬浮窗遥控拦截 ============
if not in_lock():
    sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(2.5)
    nav_to('立即锁屏')
    key('KEYCODE_DPAD_CENTER', 3.0)
report('T4-pre 遥控锁屏', in_lock())
key('KEYCODE_HOME', 6)
key('KEYCODE_DPAD_CENTER', 3)
report('T4a HOME 后确认键回锁屏（悬浮窗遥控拦截）', in_lock(), focus()[:50])
key('KEYCODE_ENTER', 3)
report('T4b ENTER 键回锁屏', in_lock())

# ============ T5 BACK ============
key('KEYCODE_BACK', 2)
report('T5 锁屏页 BACK 无效', in_lock())

# ============ T6 杂项按键 ============
for k in ('KEYCODE_MENU', 'KEYCODE_VOLUME_UP', 'KEYCODE_VOLUME_DOWN', 'KEYCODE_0', 'KEYCODE_PROG_RED'):
    key(k, 0.4)
report('T6 杂项按键不崩溃', sh('pidof com.kidslock.app').strip() != '' and in_lock())

# ============ T7 HOME 回拉 ============
key('KEYCODE_HOME', 6)
report('T7 HOME 回拉锁屏', in_lock(), focus()[:50])

# ============ 收尾：D-pad PIN 解锁 ============
report('收尾 遥控全键盘 PIN 解锁', pin_unlock_dpad())

print('\n========== TV 遥控专项 v2 汇总 ==========')
p = sum(1 for _, ok, _ in results if ok)
for n, ok, d in results:
    print(('PASS' if ok else 'FAIL') + ' | ' + n + (' | ' + d if d else ''))
print(f'===== TV 遥控专项 v2: {p} PASS / {len(results) - p} FAIL =====')
sys.exit(0 if p == len(results) else 1)
