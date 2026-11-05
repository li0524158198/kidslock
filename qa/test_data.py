#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA T1: 题库数据层校验（36 库 + labels + 每题 schema + CSV 同步一致性）"""
import json, sys, csv, io, re, unicodedata
from pathlib import Path

from qaenv import ROOT, QUESTIONS_JSON
JSON_PATHS = {
    'source': QUESTIONS_JSON,
    'android': ROOT / 'kidslock-src/app/src/main/res/raw/questions.json',
    'harmony': ROOT / 'harmony/KidsLock/entry/src/main/resources/rawfile/questions.json',
    'ios': ROOT / 'ios/KidsLock/KidsLock/questions.json',
}
CSV_DIR = ROOT / 'dist/csv'

passed, failed = [], []
def check(name, ok, detail=''):
    (passed if ok else failed).append((name, detail))
    print(('PASS' if ok else 'FAIL') + f' | {name}' + (f' | {detail}' if detail else ''))

# ---------- 1. 单一源 + 三平台 JSON 完全一致 ----------
datas = {}
for plat, p in JSON_PATHS.items():
    datas[plat] = json.loads(p.read_text(encoding='utf-8'))
check('T1.1 单一源与三平台 questions.json 内容一致',
      datas['source'] == datas['android'] == datas['harmony'] == datas['ios'])
J = datas['source']

# ---------- 2. 36 库齐全 ----------
expect_ids = {f'{s}_g{g}' for s in ('chinese', 'math', 'english') for g in range(1, 13)}
bank_ids = set(J['banks'].keys())
check('T1.2 内置库数量=36', len(bank_ids) == 36, f'实际 {len(bank_ids)}')
missing = expect_ids - bank_ids
extra = bank_ids - expect_ids
check('T1.3 库 id 集合精确匹配（chinese/math/english × g1..g12）',
      not missing and not extra, f'missing={sorted(missing)} extra={sorted(extra)}')
check('T1.4 labels 与 banks 键一致', set(J['labels'].keys()) == bank_ids)
check('T1.5 所有库非空', all(len(v) > 0 for v in J['banks'].values()),
      f'空库: {[k for k,v in J["banks"].items() if not v]}')

# ---------- 3. 每题 schema 校验 ----------
schema_errors = []
char_missing = []
dup_opt = []
empty_opt = []
for bid, arr in J['banks'].items():
    for i, it in enumerate(arr):
        q = it.get('q', '')
        opts = it.get('opts', [])
        ans = it.get('ans', -1)
        if not isinstance(q, str) or not q.strip():
            schema_errors.append(f'{bid}[{i}] 题干为空')
        if not isinstance(opts, list) or len(opts) != 4:
            schema_errors.append(f'{bid}[{i}] 选项数={len(opts) if isinstance(opts,list) else "?"} (应为4)')
            continue
        if not all(isinstance(o, str) and o.strip() for o in opts):
            empty_opt.append(f'{bid}[{i}] 存在空选项 {opts}')
        if len(set(o.strip() for o in opts)) != 4:
            dup_opt.append(f'{bid}[{i}] 选项重复 {opts}')
        if not (isinstance(ans, int) and 0 <= ans <= 3):
            schema_errors.append(f'{bid}[{i}] ans={ans} 越界')
        ch = it.get('char')
        if ch is not None and (not isinstance(ch, str) or not ch.strip()):
            schema_errors.append(f'{bid}[{i}] char 非法: {ch!r}')
        # 语文字音题应有 char 且 q 应为固定文案
        if ch and '读什么' not in q and q != ch:
            char_missing.append(f'{bid}[{i}] char={ch} 但题干={q[:20]}')
check('T1.6 每题 schema（q 非空/opts=4/ans∈0..3）', not schema_errors,
      '; '.join(schema_errors[:5]) + (f' …共{len(schema_errors)}条' if len(schema_errors) > 5 else ''))
check('T1.7 无重复选项（防止 shuffle 去重后答案错位）', not dup_opt,
      '; '.join(dup_opt[:5]) + (f' …共{len(dup_opt)}条' if len(dup_opt) > 5 else ''))
check('T1.8 无空选项', not empty_opt, '; '.join(empty_opt[:5]))

# ---------- 4. 题干重复率（同库内重复会降低出题多样性） ----------
dups_in_bank = []
for bid, arr in J['banks'].items():
    seen = {}
    for i, it in enumerate(arr):
        key = it['q'] + '|' + '|'.join(it['opts'])
        if key in seen:
            dups_in_bank.append(f'{bid}: [{seen[key]}]==[{i}] {it["q"][:20]}')
        seen[key] = i
check('T1.9 同库内无完全重复题目', not dups_in_bank,
      '; '.join(dups_in_bank[:5]) + (f' …共{len(dups_in_bank)}条' if len(dups_in_bank) > 5 else ''))

# ---------- 5. CSV 与 JSON 同步一致性 ----------
csv_files = sorted(CSV_DIR.glob('*.csv'))
check('T2.1 dist/csv 文件数=36', len(csv_files) == 36, f'实际 {len(csv_files)}')
mismatch = []
for f in csv_files:
    bid = f.stem
    if bid not in J['banks']:
        mismatch.append(f'{bid}: JSON 无此库'); continue
    rows = list(csv.reader(io.StringIO(f.read_text(encoding='utf-8-sig'), newline='')))
    if not rows or rows[0][0] != '题干':
        mismatch.append(f'{bid}: 缺表头'); continue
    body = rows[1:]
    jarr = J['banks'][bid]
    if len(body) != len(jarr):
        mismatch.append(f'{bid}: CSV {len(body)} 题 vs JSON {len(jarr)} 题'); continue
    # 逐题对比（CSV 顺序即 JSON 顺序）
    for i, (r, jit) in enumerate(zip(body, jarr)):
        if len(r) < 7:
            mismatch.append(f'{bid}[{i}] 列数 {len(r)}'); continue
        q, a, b, c, d, ans_l, big = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
        if q != jit['q']: mismatch.append(f'{bid}[{i}] 题干不一致'); continue
        if [a, b, c, d] != jit['opts']: mismatch.append(f'{bid}[{i}] 选项不一致 {r[1:5]} vs {jit["opts"]}'); continue
        if 'ABCD'[jit['ans']] != ans_l.strip().upper(): mismatch.append(f'{bid}[{i}] 答案列 {ans_l} vs {jit["ans"]}'); continue
        if (jit.get('char') or '') != big: mismatch.append(f'{bid}[{i}] 大字列 {big!r} vs {jit.get("char")!r}')
check('T2.2 36 个 CSV 与 JSON 逐题一致（题干/选项/答案/大字）', not mismatch,
      '; '.join(mismatch[:8]) + (f' …共{len(mismatch)}条' if len(mismatch) > 8 else ''))

# ---------- 6. 数学题干格式合理性（内置数学题为文本题） ----------
math_bad = []
for bid, arr in J['banks'].items():
    if not bid.startswith('math'): continue
    for i, it in enumerate(arr):
        # 数学题不应有 char 字段
        if it.get('char'):
            math_bad.append(f'{bid}[{i}] 数学题带 char={it["char"]}')
check('T1.10 数学库无大字字段', not math_bad, '; '.join(math_bad[:5]))

# ---------- 7. 语文拼音抽查（字音题：正确答案是否为该字拼音） ----------
# 内置拼音校验表（人工 + 程序生成时用 pypinyin 如可用）
try:
    from pypinyin import pinyin, Style
    HAS_PP = True
except ImportError:
    HAS_PP = False
if HAS_PP:
    py_err = []
    for bid, arr in J['banks'].items():
        if not bid.startswith('chinese'): continue
        for i, it in enumerate(arr):
            ch = it.get('char')
            if not ch: continue
            expect = pinyin(ch, style=style_tone())[0][0]
            actual = it['opts'][it['ans']]
            if expect != actual:
                py_err.append(f'{bid}[{i}] {ch}: 数据答案 {actual} ≠ pypinyin {expect}')
    check('T1.11 语文字音题答案 vs pypinyin', not py_err,
          '; '.join(py_err[:10]) + (f' …共{len(py_err)}条' if len(py_err) > 10 else ''))
else:
    print('SKIP | T1.11 语文字音题答案 vs pypinyin（未安装 pypinyin）')

def style_tone():
    from pypinyin import Style
    return Style.TONE

print(f'\n===== T1/T2 数据层: {len(passed)} PASS / {len(failed)} FAIL =====')
sys.exit(1 if failed else 0)
