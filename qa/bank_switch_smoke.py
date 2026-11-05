#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学科/年级切换 + 版本显示 冒烟（emulator-5554）。"""
import re, subprocess, sys, time

from qaenv import adb, SERIAL as SER, TMP
ADB = adb()

def dump(retries=3):
    """toast 显示期间 uiautomator dump 会失败：先删旧文件，失败则重试，杜绝读到陈旧内容。"""
    for _ in range(retries):
        subprocess.run([ADB, '-s', SER, 'shell', 'rm /sdcard/ui.xml'], capture_output=True, timeout=10)
        r = subprocess.run([ADB, '-s', SER, 'shell', 'uiautomator dump /sdcard/ui.xml'], capture_output=True, timeout=40)
        if b'dumped' not in r.stdout:
            time.sleep(1.2); continue
        subprocess.run([ADB, '-s', SER, 'pull', '/sdcard/ui.xml', TMP + '/bs.xml'], capture_output=True, timeout=40)
        try:
            data = open(TMP + '/bs.xml', encoding='utf-8').read()
        except Exception:
            time.sleep(1.2); continue
        return [(m.group(1), (int(m.group(2)) + int(m.group(4))) // 2, (int(m.group(3)) + int(m.group(5))) // 2)
                for m in re.finditer(r'text="([^"]{1,90})"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', data) if m.group(1).strip()]
    return []

def tap(x, y, wait=1.2):
    subprocess.run([ADB, '-s', SER, 'shell', f'input tap {x} {y}'], capture_output=True, timeout=30)
    time.sleep(wait)

def tap_exact(text, up=3, down=6):
    for _ in range(up):
        subprocess.run([ADB, '-s', SER, 'shell', 'input swipe 640 150 640 600 300'], capture_output=True); time.sleep(0.5)
    for _ in range(down):
        for t, x, y in dump():
            if t == text:
                tap(x, y); return True
        subprocess.run([ADB, '-s', SER, 'shell', 'input swipe 640 550 640 150 400'], capture_output=True); time.sleep(0.8)
    return False

def bank_line():
    """状态行在页面偏下方：向下滚动最多 3 屏寻找'当前题库'行，读毕滚回顶部。"""
    for _ in range(3):
        line = next((t for t, _, _ in dump() if '当前题库：' in t), '')
        if line:
            return line
        subprocess.run([ADB, '-s', SER, 'shell', 'input swipe 640 550 640 150 400'], capture_output=True)
        time.sleep(0.8)
    line = next((t for t, _, _ in dump() if '当前题库：' in t), '')
    for _ in range(4):
        subprocess.run([ADB, '-s', SER, 'shell', 'input swipe 640 150 640 600 300'], capture_output=True)
        time.sleep(0.4)
    return line

results = []
def report(name, ok, detail=''):
    results.append(ok)
    print(('PASS' if ok else 'FAIL') + f' | {name}' + (f' | {detail}' if detail else ''), flush=True)

# 0. 进入设置页（若锁屏先 PIN 解锁）
focus = subprocess.run([ADB, '-s', SER, 'shell', 'dumpsys window | grep mCurrentFocus'],
                       capture_output=True, timeout=30).stdout.decode('utf-8', 'ignore')
if 'LockScreenActivity' in focus:
    for t, x, y in dump():
        if 'PIN' in t or '家长' in t: tap(x, y, 1.2); break
    time.sleep(1)
    keys = {t: (x, y) for t, x, y in dump() if t in '0123456789'}
    for d in '1234':
        if d in keys: tap(*keys[d], wait=0.4)
    time.sleep(2)
subprocess.run([ADB, '-s', SER, 'shell', 'am start -n com.kidslock.app/.MainActivity'], capture_output=True)
time.sleep(3)

# 1. 版本显示
ver = next((t for t, _, _ in dump() if re.match(r'^v\d+\.\d+', t)), '')
report('B1 设置页显示版本号', ver == 'v1.5.1', ver)

# 2. 学科切换：语文→数学→英语（保留当前年级）
tap_exact('语文')
time.sleep(2.2)  # 等 toast 消失
base = bank_line()
m = re.search(r'当前题库：(..)·(.+?)｜', base)
grade = m.group(2) if m else '三年级'
report('B2 基线题库读取', bool(m), base)

tap_exact('数学')
time.sleep(2.2)
line = bank_line()
report('B3 点数学 → 立即切换（保留年级）', '数学·' + grade in line, line)

tap_exact('英语')
time.sleep(2.2)
line = bank_line()
report('B4 点英语 → 立即切换', '英语·' + grade in line, line)

# 3. 年级切换（当前学科联动）
tap_exact('三')
time.sleep(2.2)
line = bank_line()
report('B5 点年级 → 学科联动（英语·三）', line == '当前题库：英语·三年级｜观看时长：30 秒', repr(line))

# 4. toast 抽查（题库行已足够，跳过 toast 时机问题）
print(f'\n===== 学科切换冒烟: {sum(results)}/{len(results)} ===== ' + ('ALL PASS' if all(results) else 'HAS FAIL'))
sys.exit(0 if all(results) else 1)
