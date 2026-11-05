#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA E v2: 修正版 TV E2E（双向滚动找按钮 + 服务短名匹配 + 僵尸计时验证）"""
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
    """toast 显示期间 uiautomator dump 会静默失败并残留旧文件：先删再 dump，校验输出，必要时重试。"""
    for _ in range(3):
        subprocess.run([ADB, '-s', SER, 'shell', 'rm -f /sdcard/ui.xml'], capture_output=True, timeout=10)
        r = subprocess.run([ADB, '-s', SER, 'shell', 'uiautomator dump /sdcard/ui.xml'], capture_output=True, timeout=40)
        if b'dumped' not in r.stdout:
            time.sleep(1.2)
            continue
        subprocess.run([ADB, '-s', SER, 'pull', '/sdcard/ui.xml', TMP + '/e2e2.xml'], capture_output=True, timeout=40)
        try:
            data = open(TMP + '/e2e2.xml', encoding='utf-8').read()
        except Exception:
            time.sleep(1.2)
            continue
        return [(m.group(1), (int(m.group(2)) + int(m.group(4))) // 2, (int(m.group(3)) + int(m.group(5))) // 2)
                for m in re.finditer(r'text="([^"]{1,80})"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', data) if m.group(1).strip()]
    return []

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

def service_running():
    out = sh('dumpsys activity services com.kidslock.app')
    return 'ServiceRecord' in out and 'LockService' in out

def find(items, exact=None, contains=None):
    for t, x, y in items:
        if (exact and t == exact) or (contains and contains in t):
            return x, y
    return None

def tap_text(exact=None, contains=None, tries=8):
    """先滚回页面顶部，再逐屏向下查找并点击（TV 焦点恢复会让页面停在任意位置）"""
    for _ in range(3):
        sh('input swipe 640 150 640 600 300')
        time.sleep(0.5)
    for i in range(tries):
        items = dump()
        p = find(items, exact=exact, contains=contains)
        if p:
            tap(*p)
            return True
        sh('input swipe 640 550 640 150 400')
        time.sleep(0.9)
    return False

def unlock_pin():
    if not tap_text(exact='家长解锁', tries=3):
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
    time.sleep(1.0)
    return ok1 and ok2

def status_line():
    """逐屏向下找"当前题库：xxx｜观看时长"行（优先）或"当前状态"行，读毕滚回顶部。"""
    line = ''
    for _ in range(4):
        items = dump()
        bank = next((t for t, _, _ in items if '当前题库：' in t), '')
        if bank:
            line = bank
            break
        st = next((t for t, _, _ in items if '当前状态：' in t), '')
        if st and not line:
            line = st
        sh('input swipe 640 550 640 150 400')
        time.sleep(0.7)
    for _ in range(5):
        sh('input swipe 640 150 640 600 300')
        time.sleep(0.4)
    return line

# ===== E1 启动（接受锁屏重定向或设置页：重装保留数据时锁屏态正确恢复）=====
sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(3)
f1 = focus()
report('E1 启动（锁屏态被正确恢复/拦截绕过）', ('LockScreenActivity' in f1) or ('MainActivity' in f1), f1[:60])

ensure_unlocked()

# ===== E2 题库切换 =====
for sub, grade, expect in [('语文', '三', '语文·三年级'), ('数学', '五', '数学·五年级'), ('英语', '高三', '英语·高三')]:
    ok = switch_bank(sub, grade)
    lbl = status_line()
    report(f'E2 切换{expect}', ok and expect in lbl, lbl)

# ===== E2.5 P2-2 计时自愈验证：force-stop 后重开 App 服务应自动恢复 =====
ensure_unlocked()
tap_text(exact='30分钟'); time.sleep(0.8)
tap_text(exact='开始计时'); time.sleep(2)
svc1 = service_running()
sh('am force-stop com.kidslock.app'); time.sleep(2)
sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(3)
svc2 = service_running()
# 状态卡在页面顶部：滚顶后直接读"当前状态/剩余时间"
for _ in range(3):
    sh('input swipe 640 150 640 600 300'); time.sleep(0.4)
items = dump()
st = next((t for t, x, y in items if '当前状态：' in t), '') + ' ' + \
     next((t for t, x, y in items if '剩余时间' in t), '')
report('E2.5a 计时启动时服务运行', svc1)
report('E2.5b force-stop 后重开：服务自愈且计时保持（P2-2 修复）',
      svc2 and ('计时中' in st or '剩余时间' in st), f'svc={svc2} {st.strip()[:40]}')
tap_text(exact='停止计时'); time.sleep(1)

# ===== E3 30 秒档 → 自动锁屏 =====
ensure_unlocked()
ok30 = tap_text(exact='30秒')
lbl = status_line()
report('E3a 时长档 30 秒生效', ok30 and '30 秒' in lbl, lbl)
ok_start = tap_text(exact='开始计时'); time.sleep(2)
report('E3b 服务运行（短名匹配）', service_running(), f'开始计时点击={ok_start}')
t0 = time.time()
locked = False
while time.time() - t0 < 75:
    if in_lock():
        locked = True
        break
    time.sleep(3)
report('E3c 30 秒到时自动锁屏', locked, f'{time.time() - t0:.0f}s')

# ===== E8 HOME/BACK =====
key('KEYCODE_HOME', wait=5)
report('E8a HOME 后锁屏回拉', in_lock(), focus()[:60])
key('KEYCODE_BACK', wait=2)
report('E8b BACK 拦截', in_lock())

# ===== E9 强杀重启状态保持 =====
sh('am force-stop com.kidslock.app'); time.sleep(2)
sh('am start -n com.kidslock.app/.MainActivity'); time.sleep(4)
report('E9 锁屏状态强杀后保持', in_lock(), focus()[:60])

# ===== E4 答错归零 =====
unlock_pin()
# 解锁成功后 finishAffinity 回到桌面：重新拉起设置页再操作
ensure_unlocked()
switch_bank('语文', '三')
tap_text(exact='立即锁屏'); time.sleep(3)

# 全库题干→标答（覆盖任意题库切换）；另支持字音题（大字）与程序生成数学题（表达式重算）
AMAP = {}
for bank, arr in J['banks'].items():
    for it in arr:
        AMAP[it['q']] = it['opts'][it['ans']]

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

LOCK_FIXED = {'这个字读什么？', '家长解锁', '答对了！', '答错了，重新开始！'}

def current_answer(items):
    """返回当前题目的正确答案文本（内置题/字音题/生成数学题），未识别返回 None。"""
    texts = [t for t, _, _ in items]
    for t in texts:
        if t in AMAP and t not in LOCK_FIXED and not re.match(r'^[语数英]·', t):
            return AMAP[t]
    for t in texts:  # 字音题：单字 → 「X」的正确读音是？
        if len(t) == 1 and f'「{t}」的正确读音是？' in AMAP:
            return AMAP[f'「{t}」的正确读音是？']
    for t in texts:  # 生成数学题
        v = eval_math(t)
        if v is not None:
            return v
    return None

items = dump()
answer = current_answer(items)
for _ in range(3):  # 锁屏刚加载/反馈动画期间 dump 可能错过题目，重试
    if answer:
        break
    time.sleep(1.5)
    items = dump()
    answer = current_answer(items)
done_e4 = False
if answer:
    wrong = next(((x, y) for t, x, y in items if t != answer and len(t) <= 40
                  and t not in LOCK_FIXED and not re.match(r'^[语数英]·', t) and '已答对' not in t), None)
    if wrong:
        tap(*wrong, wait=2.5)
        items = dump()
        zero = any(re.match(r'已答对 0/\d+', t) for t, x, y in items)
        report('E4 答错归零出新题', zero)
        done_e4 = True
if not done_e4:
    report('E4 答错归零出新题', False, f'answer={answer}')

# ===== E5 连对 3 题解锁 =====
t0 = time.time()
unlocked = False
n_ok = 0
while time.time() - t0 < 150:
    if not in_lock():
        unlocked = True
        break
    items = dump()
    answer = current_answer(items)
    if not answer:
        time.sleep(2)
        continue
    p = find(items, exact=answer)
    if p:
        tap(*p, wait=3.5)
        n_ok += 1
report('E5 连对 3 题自动解锁', unlocked, f'答对 {n_ok} 次')

# ===== E6 解锁题数 5 =====
ensure_unlocked()
tap_text(exact='5题'); time.sleep(0.8)
switch_bank('语文', '三')
tap_text(exact='立即锁屏'); time.sleep(3)
items = dump()
prog = next((t for t, x, y in items if '已答对' in t), '')
report('E6 解锁题数 5（进度 0/5）', '0/5' in prog, prog)
unlock_pin()

# ===== E7 PIN 防暴力 =====
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
still_locked = in_lock()
report('E7a 连错 PIN×5 后仍锁屏', still_locked and fails_done >= 4, f'完成 {fails_done} 轮')

# 锁定期内正确 PIN 被拒（E7a 输完后键盘页仍在：直接输入，
# 不做 tap_text('家长解锁')——键盘页找不到该按钮，徒劳搜索会把 30s 锁定期耗光）
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

# 等 31 秒锁定期满（键盘页仍在则直接输，否则先打开键盘）
time.sleep(31)
digits = {}
for t, x, y in dump():
    if t in '0123456789':
        digits[t] = (x, y)
if len(digits) < 10:
    tap_text(exact='家长解锁'); time.sleep(1.5)
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

print('\n========== E2E v2 汇总 ==========')
p = sum(1 for _, ok, _ in results if ok)
for n, ok, d in results:
    print(('PASS' if ok else 'FAIL') + ' | ' + n + (' | ' + d if d else ''))
print(f'===== E2E v2: {p} PASS / {len(results) - p} FAIL =====')
sys.exit(0 if p == len(results) else 1)
