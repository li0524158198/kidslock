# -*- coding: utf-8 -*-
"""修复 JvmTests.java T4.13 块：无反斜杠正则 + 修正 ×/÷ 字符"""
import re

path = r'D:\project\kidslock\qa\jvm\src\JvmTests.java'
src = open(path, encoding='utf-8', errors='replace').read()

MUL = chr(215)   # ×
DIV = chr(247)   # ÷

# 1) 三条 Pattern 行整体重写（行级替换）
lines = src.split('\n')
out = []
for l in lines:
    if 'Pattern p2 = ' in l:
        out.append('            java.util.regex.Pattern p2 = java.util.regex.compile("([0-9]+) ([+' + MUL + DIV + '-]) ([0-9]+) = [?]$");')
    elif 'Pattern p3 = ' in l:
        out.append('            java.util.regex.Pattern p3 = java.util.regex.compile("([0-9]+) [+] ([0-9]+) - ([0-9]+) = [?]$");')
    elif 'Pattern pe = ' in l:
        out.append('            java.util.regex.Pattern pe = java.util.regex.compile("^解方程：([0-9]+)x [+] ([0-9]+) = ([0-9]+)，x = [?]$");')
    elif 'op.equals(' in l and ('脳' in l or MUL in l):
        out.append(l.replace('脳', MUL))
    elif 'mulSample.isEmpty()' in l and '脳' in l:
        out.append(l.replace('脳', MUL))
    elif '答案=a' in l and '脳' in l:
        out.append(l.replace('脳', MUL))
    else:
        out.append(l)
src = '\n'.join(out)

# 2) 兜底：全文替换坏字符
src = src.replace('脳', MUL).replace('枚', DIV)

open(path, 'w', encoding='utf-8', newline='\n').write(src)
print('patched; contains bad char:', '脳' in src, '; MUL count:', src.count(MUL))
