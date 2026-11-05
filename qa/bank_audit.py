#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA T5: 题库正确性 + 重复审计（对单一源 data/questions.json）

检测维度：
  A. 数学可计算题：脚本重算答案 vs 数据标答          → FAIL 级
  B. 语文拼音题（声母/韵母/读音）：pypinyin 校验      → WARN 级（多音字/教材差异可能误报，逐条人工复核）
  C. 重复三级：
     C1 同库题干重复                                  → FAIL 级
     C2 跨库完全一致（题干+选项都相同）               → FAIL 级
     C3 跨库同题干不同选项                            → INFO（英语词汇跨年级复现等，多为合理设计）
  D. schema 速查：ans 越界 / 选项重复 / 空选项        → FAIL 级

拼音校验需要 pypinyin（未安装则该项 SKIP，不影响退出码）：
  pip install pypinyin
  注意 Windows 下 PATH 里的 python 与 pip 可能不是同一解释器，用 `python -m pip` 安装。

用法：
  python qa/bank_audit.py
证据输出：qa/reports/bank_audit.json
"""
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qaenv import ROOT, QUESTIONS_JSON  # noqa: E402

REPORT_JSON = ROOT / 'qa' / 'reports' / 'bank_audit.json'

# ---------- 拼音（可选依赖） ----------
try:
    from pypinyin import lazy_pinyin, Style
    HAS_PINYIN = True
except ImportError:
    HAS_PINYIN = False


def strip_tone(s: str) -> str:
    """去掉声调符号（ū→u，ī→i）。"""
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if not unicodedata.combining(c))


# ---------- 数学重算 ----------
P2 = re.compile(r'^([0-9]+)\s*([+×÷\-])\s*([0-9]+)\s*=\s*[?？]$')
P3 = re.compile(r'^([0-9]+)\s*\+\s*([0-9]+)\s*-\s*([0-9]+)\s*=\s*[?？]$')
PE = re.compile(r'^解方程：\s*([0-9]+)x\s*\+\s*([0-9]+)\s*=\s*([0-9]+)，\s*x\s*=\s*[?？]$')


def recompute(q: str):
    """能重算返回 int，无法解析返回 None（文字题/概念题）。"""
    m = P3.match(q)
    if m:
        return int(m.group(1)) + int(m.group(2)) - int(m.group(3))
    m = PE.match(q)
    if m:
        a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return (c - b) // a if a and (c - b) % a == 0 else None
    m = P2.match(q)
    if m:
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        if op == '+':
            return a + b
        if op == '-':
            return a - b
        if op == '×':
            return a * b
        if op == '÷':
            return a // b if b and a % b == 0 else None
    return None


# ---------- 拼音校验 ----------
PINITIAL = re.compile(r'声母')
PFINAL = re.compile(r'韵母')
PFULL = re.compile(r'读音|拼音')


def pinyin_check(it, evidence):
    """返回 (状态, 说明)。状态: ok / warn / skip。"""
    if not HAS_PINYIN:
        return 'skip', '未安装 pypinyin'
    q = it['q']
    char = it.get('char')
    if not char:
        m = re.match(r'「(.)」', q)
        if not m:
            return 'skip', '无大字且题干未标注汉字'
        char = m.group(1)
    marked = it['opts'][it['ans']]
    if PINITIAL.search(q):
        expect = lazy_pinyin(char, style=Style.INITIALS, strict=False)[0]
        ok = expect == marked
        kind = '声母'
    elif PFINAL.search(q):
        expect = lazy_pinyin(char, style=Style.FINALS, strict=False)[0]
        # 韵母选项可能带调（ün/ūn），两边都去调比较
        ok = strip_tone(expect) == strip_tone(marked)
        kind = '韵母'
    elif PFULL.search(q):
        expect = lazy_pinyin(char, style=Style.TONE)[0]
        ok = expect == marked
        kind = '读音'
    else:
        return 'skip', ''
    if ok:
        return 'ok', ''
    return 'warn', f'{kind}题：「{char}」pypinyin={expect!r} vs 标答={marked!r}（多音字/教材读音差异需人工复核）'


def main() -> int:
    data = json.loads(QUESTIONS_JSON.read_text(encoding='utf-8'))
    banks = data['banks']

    fails, warns = [], []
    evidence = {'math_checked': 0, 'math_wrong': [], 'pinyin_checked': 0,
                'pinyin_warn': [], 'schema_bad': [], 'dup_same_bank': [],
                'dup_cross_exact': [], 'dup_cross_qtext': []}

    # ---------- A/B/D：逐题 ----------
    for bid, arr in banks.items():
        for i, it in enumerate(arr):
            where = f'{bid}[{i}]'
            opts, ans = it.get('opts', []), it.get('ans', -1)
            # D. schema
            if not (isinstance(ans, int) and 0 <= ans <= 3):
                evidence['schema_bad'].append(f'{where} ans={ans} 越界')
            if len(set(opts)) != 4:
                evidence['schema_bad'].append(f'{where} 选项重复 {opts}')
            # A. 数学重算
            if bid.startswith('math'):
                expect = recompute(it['q'])
                if expect is not None:
                    evidence['math_checked'] += 1
                    try:
                        marked = int(str(opts[ans]).strip())
                    except (ValueError, IndexError):
                        marked = None
                    if marked != expect:
                        evidence['math_wrong'].append(
                            {'where': where, 'q': it['q'], 'marked': opts[ans], 'expect': expect})
            # B. 拼音
            if bid.startswith('chinese') and (PINITIAL.search(it['q']) or PFINAL.search(it['q']) or PFULL.search(it['q'])):
                st, msg = pinyin_check(it, evidence)
                if st == 'ok':
                    evidence['pinyin_checked'] += 1
                elif st == 'warn':
                    evidence['pinyin_checked'] += 1
                    evidence['pinyin_warn'].append({'where': where, 'q': it['q'], 'why': msg})

    # ---------- C. 重复 ----------
    for bid, arr in banks.items():
        for q, c in Counter(it['q'] for it in arr).items():
            if c > 1:
                evidence['dup_same_bank'].append({'bank': bid, 'q': q, 'count': c})
    exact_map = defaultdict(set)
    text_map = defaultdict(set)
    for bid, arr in banks.items():
        for it in arr:
            exact_map[(it['q'], tuple(it['opts']))].add(bid)
            text_map[it['q']].add(bid)
    for k, v in exact_map.items():
        if len(v) > 1:
            evidence['dup_cross_exact'].append({'banks': sorted(v), 'q': k[0]})
    exact_dup_qs = {x['q'] for x in evidence['dup_cross_exact']}
    for k, v in text_map.items():
        if len(v) > 1 and k not in exact_dup_qs:
            evidence['dup_cross_qtext'].append({'banks': sorted(v), 'q': k})

    # ---------- 汇总 ----------
    total = sum(len(v) for v in banks.values())
    print(f'题库总量: {total} 题 / {len(banks)} 库\n')
    all_pass = True
    hard_checks = [
        ('T5.A 数学可计算题答案重算', evidence['math_checked'], evidence['math_wrong']),
        ('T5.C1 同库题干无重复', len(banks), evidence['dup_same_bank']),
        ('T5.C2 跨库无完全一致题目', len(exact_map), evidence['dup_cross_exact']),
    ]
    for name, checked, bad in hard_checks:
        print(f'{"PASS" if not bad else "FAIL"} | {name} | {checked} 检出 {len(bad)} 问题')
        if bad:
            all_pass = False
            for x in bad[:10]:
                print(f'      {x}')
            if len(bad) > 10:
                print(f'      …共 {len(bad)} 条，详见 {REPORT_JSON.name}')
    # 拼音：WARN 级（多音字可能误报，人工复核），不影响退出码
    if HAS_PINYIN:
        print(f'{"PASS" if not evidence["pinyin_warn"] else "WARN"} | T5.B 拼音题校验（pypinyin）'
              f' | {evidence["pinyin_checked"]} 检出 {len(evidence["pinyin_warn"])} 疑似')
        for x in evidence['pinyin_warn'][:10]:
            print(f'      {x["where"]} {x["q"]} → {x["why"]}')
        if len(evidence['pinyin_warn']) > 10:
            print(f'      …共 {len(evidence["pinyin_warn"])} 条，详见 {REPORT_JSON.name}')
    else:
        print('SKIP | T5.B 拼音题校验 | 未安装 pypinyin（pip install pypinyin）')
    if evidence['dup_cross_qtext']:
        print(f'INFO | T5.C3 跨库同题干不同选项 {len(evidence["dup_cross_qtext"])} 处'
              f'（英语词汇跨年级复现等，属合理设计，仅记录）')
    if evidence['schema_bad']:
        print(f'FAIL | T5.D schema | {len(evidence["schema_bad"])} 处')
        all_pass = False
        for x in evidence['schema_bad'][:10]:
            print(f'      {x}')

    REPORT_JSON.write_text(json.dumps(evidence, ensure_ascii=False, indent=1), encoding='utf-8')
    verdict = 'PASS' if all_pass else 'FAIL'
    print(f'\n===== T5 题库审计: {verdict} =====（证据 → qa/reports/bank_audit.json）')
    return 0 if all_pass else 1


if __name__ == '__main__':
    sys.exit(main())
