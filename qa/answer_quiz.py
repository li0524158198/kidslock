#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""答题辅助：读取锁屏题目，选择指定选项（正确/错误），返回进度"""
import json, re, subprocess, sys

from qaenv import adb, TMP
ADB = adb()
import os as _os
import sys as _sys
# 默认 TV 模拟器 5556（原行为）；可用 第2个参数 或 KIDSLOCK_SERIAL 覆盖
SER = _sys.argv[2] if len(_sys.argv) > 2 else _os.environ.get('KIDSLOCK_SERIAL', 'emulator-5556')
MAP = json.load(open(TMP + '/pinyin_map.json', encoding='utf-8'))

def get_ui():
    subprocess.run([ADB, '-s', SER, 'shell', 'uiautomator dump /sdcard/ui.xml'],
                   capture_output=True, timeout=30)
    r = subprocess.run([ADB, '-s', SER, 'shell', 'cat /sdcard/ui.xml'],
                       capture_output=True, timeout=30)
    return r.stdout.decode('utf-8', 'ignore')

def tap(x, y):
    subprocess.run([ADB, '-s', SER, 'shell', f'input tap {x} {y}'],
                   capture_output=True, timeout=30)

def parse(data):
    texts = []
    for m in re.finditer(r'text="([^"]{1,24})"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', data):
        t, x1, y1, x2, y2 = m.group(1), *map(int, m.groups()[1:])
        texts.append((t, (x1+x2)//2, (y1+y2)//2, y1))
    return texts

def get_question():
    """返回 (汉字, [(选项文本,x,y)...], 进度文本)"""
    texts = parse(get_ui())
    ch = None; opts = []; prog = ''
    for t, x, y, _ in texts:
        if len(t) == 1 and t in MAP:
            ch = (t, x, y)
        elif re.fullmatch(r'[A-ZĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛ]{1,5}', t):
            opts.append((t, x, y))
        elif '已答对' in t:
            prog = t
    return ch, opts, prog

def answer(wrong=False):
    ch, opts, prog = get_question()
    if not ch or not opts:
        print('  [!] 未识别到题目', 'ch=', ch, 'opts=', opts)
        return None
    correct = MAP[ch[0]]
    target = None
    for t, x, y in opts:
        if (t.lower() == correct) != wrong:  # wrong=True 时选拼音不匹配的
            target = (t, x, y)
            break
    if target is None and wrong:
        # 都匹配不了就选第一个（不会发生：正确项只有一个）
        target = opts[0]
    print(f"  汉字[{ch[0]}] 正确答案[{correct}] -> 选择[{target[0]}]({'故意答错' if wrong else '答对'})  {prog}")
    tap(target[1], target[2])
    return True

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'right'
    answer(wrong=(mode == 'wrong'))
    # 等待反馈+下一题
    import time
    time.sleep(2.5 if not (mode=='wrong') else 3.5)
