#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
闭环冒烟：答题解锁 → 自动继续下一轮计时 → 到点再锁 → PIN 解锁（家长接管，计时停止）。
用法：python auto_continue_smoke.py  （模拟器 emulator-5554 在线，已安装新 APK）
"""
import json, re, subprocess, sys, time

from qaenv import adb, SERIAL as SER, TMP, load_questions
ADB = adb()
J = load_questions()

# 全库题干 → 标答
AMAP = {}
for bank, items in J['banks'].items():
    for it in items:
        AMAP[it['q']] = it['opts'][it['ans']]

def sh(cmd, timeout=40):
    return subprocess.run([ADB, '-s', SER, 'shell', cmd], capture_output=True, timeout=timeout).stdout.decode('utf-8', 'ignore')

def dump():
    subprocess.run([ADB, '-s', SER, 'shell', 'uiautomator dump /sdcard/ui.xml'], capture_output=True, timeout=40)
    subprocess.run([ADB, '-s', SER, 'pull', '/sdcard/ui.xml', TMP + '/acs.xml'], capture_output=True, timeout=40)
    try:
        data = open(TMP + '/acs.xml', encoding='utf-8').read()
    except Exception:
        return []
    return [(m.group(1), (int(m.group(2)) + int(m.group(4))) // 2, (int(m.group(3)) + int(m.group(5))) // 2)
            for m in re.finditer(r'text="([^"]{1,90})"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', data) if m.group(1).strip()]

def tap(x, y, wait=1.2):
    subprocess.run([ADB, '-s', SER, 'shell', f'input tap {x} {y}'], capture_output=True, timeout=30)
    time.sleep(wait)

def focus():
    return sh('dumpsys window | grep mCurrentFocus')

def svc():
    out = sh('dumpsys activity services com.kidslock.app')
    return 'ServiceRecord' in out and 'LockService' in out

def tap_exact(text, up=3, down=8):
    for _ in range(up):
        subprocess.run([ADB, '-s', SER, 'shell', 'input swipe 640 150 640 600 300'], capture_output=True); time.sleep(0.5)
    for _ in range(down):
        for t, x, y in dump():
            if t == text:
                tap(x, y); return True
        subprocess.run([ADB, '-s', SER, 'shell', 'input swipe 640 550 640 150 400'], capture_output=True); time.sleep(0.8)
    return False

def eval_math(text):
    m = re.match(r'^(\d+) \+ (\d+) = \?$', text)
    if m: return str(int(m.group(1)) + int(m.group(2)))
    m = re.match(r'^(\d+) - (\d+) = \?$', text)
    if m: return str(int(m.group(1)) - int(m.group(2)))
    m = re.match(r'^(\d+) × (\d+) = \?$', text)
    if m: return str(int(m.group(1)) * int(m.group(2)))
    m = re.match(r'^(\d+) ÷ (\d+) = \?$', text)
    if m and int(m.group(1)) % int(m.group(2)) == 0: return str(int(m.group(1)) // int(m.group(2)))
    m = re.match(r'^(\d+) \+ (\d+) - (\d+) = \?$', text)
    if m: return str(int(m.group(1)) + int(m.group(2)) - int(m.group(3)))
    m = re.match(r'^解方程：(\d+)x \+ (\d+) = (\d+)，x = \?$', text)
    if m and (int(m.group(3)) - int(m.group(2))) % int(m.group(1)) == 0:
        return str((int(m.group(3)) - int(m.group(2))) // int(m.group(1)))
    return None

FIXED = {'这个字读什么？', '家长PIN解锁', '答对了！', '答错了，重新开始！'}

def solve_once():
    """读锁屏题目，点正确选项。返回 (进度文本, 是否点中)。"""
    items = dump()
    texts = [t for t, _, _ in items]
    progress = next((t for t in texts if re.match(r'已答对 \d+/\d+', t)), '')
    # 题干：先按 JSON 精确匹配，再识别字音题/生成题
    qtext = None; answer = None
    for t in texts:
        if t in FIXED or re.match(r'已答对 \d+/\d+', t) or re.match(r'^[语数英]·.+', t) or t.startswith('自定义·'):
            continue
        if t in AMAP:
            qtext, answer = t, AMAP[t]; break
    if answer is None:
        # 字音题：大字 = 单字符文本，q = 「X」的正确读音是？
        for t in texts:
            if len(t) == 1 and f'「{t}」的正确读音是？' in AMAP:
                answer = AMAP[f'「{t}」的正确读音是？']; break
    if answer is None:
        # 生成数学题：题干匹配 eval
        for t in texts:
            v = eval_math(t)
            if v is not None:
                answer = v; break
    if answer is None:
        return progress, False
    for t, x, y in items:
        if t == answer:
            tap(x, y, wait=1.6)
            return progress, True
    return progress, False

def pin_unlock():
    items = dump()
    for t, x, y in items:
        if 'PIN' in t or '家长' in t:
            tap(x, y, wait=1.2); break
    time.sleep(1)
    keys = {t: (x, y) for t, x, y in dump() if t in '0123456789'}
    for d in '1234':
        if d in keys: tap(*keys[d], wait=0.5)
    time.sleep(2)

results = []
def report(name, ok, detail=''):
    results.append(ok)
    print(('PASS' if ok else 'FAIL') + f' | {name}' + (f' | {detail}' if detail else ''), flush=True)

# ===== 0. 清状态：若已锁屏先 PIN 解锁；确保未计时 =====
if 'LockScreenActivity' in focus():
    pin_unlock()
sh('am force-stop com.kidslock.app')
subprocess.run([ADB, '-s', SER, 'shell', 'am start -n com.kidslock.app/.MainActivity'], capture_output=True)
time.sleep(3)
print('确保 自动继续:开 / 30秒档 / 3题档 ...')
# 若"自动继续"处于关闭状态则点击开启（已开启时不动作）
items = dump()
auto_texts = {t for t, x, y in items}
if not any('自动继续：已开启' in t for t in auto_texts):
    if not tap_exact('自动继续：已关闭'):
        print('WARN: 未找到自动继续开关按钮')
tap_exact('30秒'); tap_exact('3题')
print('点 立即锁屏:', tap_exact('立即锁屏'))
time.sleep(2)
report('S1 立即锁屏生效', 'LockScreenActivity' in focus(), focus().strip()[:60])

# ===== 1. 答题解锁循环 =====
required = 3
solved = 0
for i in range(20):
    items = dump()
    prog = next((t for t, _, _ in items if re.match(r'已答对 \d+/\d+', t)), '')
    if 'LockScreenActivity' not in focus():
        break
    m = re.match(r'已答对 (\d+)/(\d+)', prog)
    if m: required = int(m.group(2))
    progress, hit = solve_once()
    if not hit:
        report(f'S2 答题 第{i+1}轮', False, '未识别题目/答案')
        sys.exit(1)
    solved += 1
report('S2 答题解锁（连对 %d 题）' % required, 'LockScreenActivity' not in focus(), f'共答 {solved} 题')

# ===== 2. 自动继续：服务重启 + 计时中 =====
time.sleep(2)
healed = svc()
subprocess.run([ADB, '-s', SER, 'shell', 'am start -n com.kidslock.app/.MainActivity'], capture_output=True)
time.sleep(2.5)
items = dump()
status = [t for t, _, _ in items if '当前状态' in t or '剩余时间' in t]
report('S3 解锁后自动继续：服务运行', healed)
report('S3b 解锁后自动继续：状态计时中', any('计时中' in t for t in status), str(status))

# ===== 3. 等到点再次自动锁屏 =====
sh('input keyevent KEYCODE_HOME'); time.sleep(1)
locked_again = False
for _ in range(30):
    time.sleep(2)
    if 'LockScreenActivity' in focus():
        locked_again = True; break
report('S4 到点再次自动锁屏（闭环）', locked_again, focus().strip()[:60])

# ===== 4. PIN 解锁 = 家长接管，计时停止 =====
pin_unlock()
time.sleep(1.5)
subprocess.run([ADB, '-s', SER, 'shell', 'am start -n com.kidslock.app/.MainActivity'], capture_output=True)
time.sleep(2.5)
items = dump()
status = [t for t, _, _ in items if '当前状态' in t]
report('S5 PIN 解锁后计时停止（家长接管）', any('未计时' in t for t in status), str(status))

ok = all(results)
print(f'\n===== 自动继续闭环冒烟: {sum(results)}/{len(results)} ===== ' + ('ALL PASS' if ok else 'HAS FAIL'))
sys.exit(0 if ok else 1)
