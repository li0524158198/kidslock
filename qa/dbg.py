#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交互式调试小工具：dump/tap/focus/logcat"""
import re, subprocess, sys, time

from qaenv import adb, SERIAL as SER, TMP
ADB = adb()

def sh(cmd, timeout=40):
    return subprocess.run([ADB, '-s', SER, 'shell', cmd], capture_output=True, timeout=timeout).stdout.decode('utf-8', 'ignore')

def dump():
    subprocess.run([ADB, '-s', SER, 'shell', 'uiautomator dump /sdcard/ui.xml'], capture_output=True, timeout=40)
    subprocess.run([ADB, '-s', SER, 'pull', '/sdcard/ui.xml', TMP + '/dbg.xml'], capture_output=True, timeout=40)
    data = open(TMP + '/dbg.xml', encoding='utf-8').read()
    out = []
    for m in re.finditer(r'text="([^"]{1,80})"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', data):
        t, x1, y1, x2, y2 = m.group(1), *map(int, m.groups()[1:])
        if t.strip():
            out.append((t, (x1 + x2) // 2, (y1 + y2) // 2))
    return out

def tap(x, y, wait=1.0):
    subprocess.run([ADB, '-s', SER, 'shell', f'input tap {x} {y}'], capture_output=True, timeout=30)
    time.sleep(wait)

def find_tap(exact=None, contains=None, tries=3):
    for _ in range(tries):
        items = dump()
        for t, x, y in items:
            if (exact and t == exact) or (contains and contains in t):
                tap(x, y)
                return t
    return None

def focus():
    return sh('dumpsys window | grep mCurrentFocus').strip()

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'dump'
    if cmd == 'dump':
        for t, x, y in dump():
            print(f'{t!r} @ ({x},{y})')
    elif cmd == 'tap':
        find_tap(exact=sys.argv[2] if len(sys.argv) < 5 or sys.argv[4] == 'exact' else None,
                 contains=sys.argv[2] if len(sys.argv) >= 5 and sys.argv[4] == 'in' else None)
        print(focus()[:90])
    elif cmd == 'focus':
        print(focus())
    elif cmd == 'svc':
        print(sh('dumpsys activity services com.kidslock.app | grep -E "ServiceRecord|app=" | head -5'))
    elif cmd == 'log':
        n = sys.argv[2] if len(sys.argv) > 2 else '80'
        print(sh(f'logcat -d -t {n} | grep -iE "kidslock|FATAL|AndroidRuntime" | tail -40'))
