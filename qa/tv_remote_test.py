#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA TV: 遥控器（D-pad）专项测试——全程仅用按键，模拟真实 TV 无触屏交互
覆盖：Leanback 启动入口 / 设置页 D-pad 导航与确认 / 锁屏页遥控答题 /
悬浮窗遥控拦截 / BACK 拦截 / 杂项按键健壮性 / HOME 回拉"""
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
    """抓 text/focused/clickable/bounds"""
    subprocess.run([ADB, '-s', SER, 'shell', 'uiautomator dump /sdcard/ui.xml'], capture_output=True, timeout=40)
    subprocess.run([ADB, '-s', SER, 'pull', '/sdcard/ui.xml', TMP + '/tv.xml'], capture_output=True, timeout=40)
    try:
        data = open(TMP + '/tv.xml', encoding='utf-8').read()
    except Exception:
        return []
    out = []
    for m in re.finditer(r'<node[^>]*?text="([^"]{0,80})"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*?/>', data):
        t = m.group(1)
        x1, y1, x2, y2 = map(int, m.groups()[1:])
        # 属性在 text 与 bounds 之外，重新在整段里找 focused/clickable
        seg = m.group(0)
        focused = 'focused="true"' in seg
        clickable = 'clickable="true"' in seg
        if t.strip() or focused:
            out.append({'text': t, 'x': (x1 + x2) // 2, 'y': (y1 + y2) // 2,
                        'focused': focused, 'clickable': clickable})
    return out

def key(k, wait=0.7):
    subprocess.run([ADB, '-s', SER, 'shell', f'input keyevent {k}'], capture_output=True, timeout=30)
    time.sleep(wait)

def focus():
    return sh('dumpsys window | grep mCurrentFocus')

def in_lock():
    return 'LockScreenActivity' in focus()

def in_settings():
    return 'MainActivity' in focus()

def focused_text():
    for n in dump_nodes():
        if n['focused'] and n['text'].strip():
            return n['text']
    return None

def pin_unlock_by_key():
    """遥控器 PIN 解锁：D-pad 导航数字键盘 + CENTER 确认（数字键也可直接按 KEYCODE_1..4）"""
    # 锁屏 PIN 界面用物理数字键更快：TV 遥控有数字键
    if not any(n['text'] == '家长解锁' for n in dump_nodes()):
        return False
    # 用 D-pad 选中 家长解锁（焦点遍历），这里简化：TAB 键通常也可移动焦点
    # 遥控风格：反复 DPAD 导航找家长解锁太长，采用数字键路径：先 CENTER 激活当前焦点若为家长解锁
    # 实测路径：按 DPAD 导航直到焦点在 家长解锁 → CENTER
    for _ in range(30):
        t = focused_text()
        if t == '家长解锁':
            key('KEYCODE_DPAD_CENTER', 1.8)
            break
        key('KEYCODE_DPAD_DOWN' if _ % 3 else 'KEYCODE_DPAD_RIGHT')
    else:
        return False
    # PIN 数字键盘：用物理数字键 1 2 3 4（TV 遥控标准配置）
    for d in ('KEYCODE_1', 'KEYCODE_2', 'KEYCODE_3', 'KEYCODE_4'):
        key(d, 0.4)
    time.sleep(2.5)
    return not in_lock()

# ============ T1 Leanback 启动器入口 ============
sh('settings put secure screensaver_enabled 0')
subprocess.run([ADB, '-s', SER, 'install', '-r', APK], capture_output=True, timeout=120)
r = subprocess.run([ADB, '-s', SER, 'shell',
                    'am start -a android.intent.action.MAIN -c android.intent.category.LEANBACK_LAUNCHER -n com.kidslock.app/.MainActivity'],
                   capture_output=True, timeout=30)
time.sleep(3)
f = focus()
ok = 'com.kidslock.app' in f
report('T1 Leanback 启动器入口启动应用', ok, f[:60])

# 若处于锁屏则先解锁
if in_lock():
    pin_unlock_by_key()
    sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(2)

# ============ T2 设置页 D-pad 导航 ============
# 回顶：多次 DPAD_UP
for _ in range(15):
    key('KEYCODE_DPAD_UP', 0.25)
visited, stuck = [], 0
prev = None
for i in range(40):
    t = focused_text()
    if t is not None and t != prev:
        visited.append(t)
    if t == prev and t is not None:
        stuck += 1
    else:
        stuck = 0
    prev = t
    if stuck >= 6:  # 到底了（连续 6 次焦点不动）
        break
    key('KEYCODE_DPAD_DOWN', 0.3)
report('T2a 设置页 D-pad 向下导航焦点可遍历', len(visited) >= 8,
       f'{len(visited)} 个焦点站: {" > ".join(visited[:10])}')

# D-pad 导航到 立即锁屏 并 CENTER
found_lock_btn = False
for _ in range(45):
    t = focused_text()
    if t == '立即锁屏':
        found_lock_btn = True
        break
    key('KEYCODE_DPAD_DOWN' if _ % 2 else 'KEYCODE_DPAD_RIGHT', 0.25)
if found_lock_btn:
    key('KEYCODE_DPAD_CENTER', 3.0)
    report('T2b 遥控器选中「立即锁屏」+ 确认键进入锁屏', in_lock(), focus()[:50])
else:
    report('T2b 遥控器选中「立即锁屏」+ 确认键进入锁屏', False, '未导航到按钮')

# ============ T3 锁屏页遥控答题（语文·三 已选或任意内置语文库）============
AMAPS = {}
for bid in ('chinese_g1', 'chinese_g2', 'chinese_g3'):
    AMAPS.update({it['q']: it['opts'][it['ans']] for it in QJ['banks'][bid]})

def answer_by_remote(timeout_s=90):
    """D-pad 答一题：题干→找到正确答案→导航→CENTER"""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        nodes = dump_nodes()
        q = next((n['text'] for n in nodes if n['text'] in AMAPS), None)
        if q is None:
            time.sleep(1.5)
            continue
        correct = AMAPS[q]
        target = next((n for n in nodes if n['text'] == correct and n['clickable']), None)
        if not target:
            continue
        # 计算目标相对焦点方向的近似导航：行=UP/DOWN，列=LEFT/RIGHT（2x2 网格）
        for _ in range(20):
            nodes = dump_nodes()
            foc = next((n for n in nodes if n['focused'] and n['clickable']), None)
            if foc and foc['text'] == correct:
                break
            if foc is None:
                key('KEYCODE_DPAD_UP', 0.4)
                continue
            dy = target['y'] - foc['y']
            dx = target['x'] - foc['x']
            if abs(dy) > 40:
                key('KEYCODE_DPAD_DOWN' if dy > 0 else 'KEYCODE_DPAD_UP', 0.35)
            elif abs(dx) > 40:
                key('KEYCODE_DPAD_RIGHT' if dx > 0 else 'KEYCODE_DPAD_LEFT', 0.35)
            else:
                break
        key('KEYCODE_DPAD_CENTER', 2.8)
        return True
    return False

if in_lock():
    # 答错一题：导航到错误选项（干扰项）
    nodes = dump_nodes()
    q = next((n['text'] for n in nodes if n['text'] in AMAPS), None)
    wrong_done = False
    if q:
        correct = AMAPS[q]
        cand = [n for n in nodes if n['clickable'] and n['text'] != correct
                and n['text'] not in ('家长解锁',) and len(n['text']) <= 40 and '已答对' not in n['text']]
        if cand:
            target = cand[0]
            for _ in range(20):
                nodes = dump_nodes()
                foc = next((n for n in nodes if n['focused'] and n['clickable']), None)
                if foc and foc['text'] == target['text']:
                    break
                if foc is None:
                    key('KEYCODE_DPAD_UP', 0.4); continue
                dy, dx = target['y'] - foc['y'], target['x'] - foc['x']
                if abs(dy) > 40: key('KEYCODE_DPAD_DOWN' if dy > 0 else 'KEYCODE_DPAD_UP', 0.35)
                elif abs(dx) > 40: key('KEYCODE_DPAD_RIGHT' if dx > 0 else 'KEYCODE_DPAD_LEFT', 0.35)
                else: break
            key('KEYCODE_DPAD_CENTER', 3.0)
            prog = [n['text'] for n in dump_nodes() if '已答对' in n['text']]
            report('T3a 遥控答错归零出新题', any(re.search(r'已答对 0/\d', t) for t in prog), str(prog))
            wrong_done = True
    if not wrong_done:
        report('T3a 遥控答错归零出新题', False, '未捕获题目')

    # 遥控连对解锁（题目库可能不是 g3——AMAPS 覆盖 g1-g3 语文；若题目不在映射则报不出）
    t0 = time.time(); unlocked = False; n_ok = 0
    while time.time() - t0 < 240:
        if not in_lock():
            unlocked = True; break
        if answer_by_remote(20):
            n_ok += 1
    report('T3b 遥控器连对 N 题自动解锁', unlocked, f'遥控答对 {n_ok} 次')

# ============ T4 悬浮窗遥控拦截 ============
if not in_lock():
    sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(2)
    # D-pad 到立即锁屏
    for _ in range(45):
        if focused_text() == '立即锁屏':
            break
        key('KEYCODE_DPAD_DOWN' if _ % 2 else 'KEYCODE_DPAD_RIGHT', 0.25)
    key('KEYCODE_DPAD_CENTER', 3.0)
report('T4-pre 遥控锁屏', in_lock())
key('KEYCODE_HOME', 5)   # 回 TV 桌面 → 悬浮窗覆盖 + 守护服务拉回
key('KEYCODE_DPAD_CENTER', 3)  # 悬浮窗上按确认 → 应打开锁屏
report('T4a HOME 后按确认键回到锁屏（悬浮窗遥控拦截）', in_lock(), focus()[:50])
key('KEYCODE_ENTER', 3)
report('T4b ENTER 键同样回锁屏', in_lock())

# ============ T5 BACK 拦截 ============
key('KEYCODE_BACK', 2)
report('T5 锁屏页 BACK 键无效', in_lock())

# ============ T6 杂项按键健壮性 ============
for k in ('KEYCODE_MENU', 'KEYCODE_VOLUME_UP', 'KEYCODE_VOLUME_DOWN', 'KEYCODE_0', 'KEYCODE_PROG_RED'):
    key(k, 0.5)
alive = sh('pidof com.kidslock.app').strip() != ''
report('T6 杂项按键不崩溃（进程存活）', alive and in_lock())

# ============ T7 HOME 回拉（TV alias）============
key('KEYCODE_HOME', 6)
report('T7 HOME 键回拉锁屏', in_lock(), focus()[:50])

# 收尾：PIN 解锁（数字键路径）
if in_lock():
    nodes = dump_nodes()
    if not any(n['text'].isdigit() for n in nodes):
        # 回答题界面找 家长解锁
        for _ in range(30):
            if focused_text() == '家长解锁':
                key('KEYCODE_DPAD_CENTER', 1.8); break
            key('KEYCODE_DPAD_DOWN' if _ % 3 else 'KEYCODE_DPAD_RIGHT', 0.3)
    for d in ('KEYCODE_1', 'KEYCODE_2', 'KEYCODE_3', 'KEYCODE_4'):
        key(d, 0.4)
    time.sleep(2.5)
    report('收尾 遥控数字键 PIN 解锁', not in_lock())

print('\n========== TV 遥控专项汇总 ==========')
p = sum(1 for _, ok, _ in results if ok)
for n, ok, d in results:
    print(('PASS' if ok else 'FAIL') + ' | ' + n + (' | ' + d if d else ''))
print(f'===== TV 遥控专项: {p} PASS / {len(results) - p} FAIL =====')
sys.exit(0 if p == len(results) else 1)
