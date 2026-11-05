# -*- coding: utf-8 -*-
"""校验 data/exam/webq_*.jsonl 并生成可直接导入 KidsLock 的真题 CSV。

注意：真题已由 scripts/gen_question_banks.py 并入内置题库（data/questions.json），
本脚本生成的 CSV 用于旧版本 App 手动导入或单独分发，不再是真题的唯一分发渠道。

用法: python scripts/build_exam_csv.py [jsonl_dir] [out_dir]
默认: jsonl_dir = data/exam, out_dir = dist/csv_exam
输出: chinese_g1..6.csv / math_g1..6.csv / english_g1..6.csv (UTF-8 BOM + CRLF)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBJECTS = {"chinese": "语文", "math": "数学", "english": "英语"}
GRADES = range(1, 7)
FORBIDDEN = [",", '"', "\n", "\r"]  # 撇号（It's）在朴素分割下安全，允许
LETTERS = "ABCD"
TARGET_PER_GRADE = 30


def bad_chars(s):
    return sorted({ch for ch in FORBIDDEN if ch in s})


def validate_item(it, subject, grade, errors, seen_q):
    where = f"{subject} g{grade}"
    for key in ("grade", "q", "opts", "ans", "big", "src"):
        if key not in it:
            errors.append(f"{where}: 缺字段 {key}")
            return
    if not (1 <= it["grade"] <= 6):
        errors.append(f"{where}: grade 非法 {it['grade']}")
        return
    q = str(it["q"]).strip()
    if not q:
        errors.append(f"{where}: 题干为空")
        return
    if len(q) > 50:
        errors.append(f"{where}: 题干超长({len(q)}) {q[:20]}…")
    bc = bad_chars(q)
    if bc:
        errors.append(f"{where}: 题干含非法字符 {bc}: {q[:30]}")
    if q in seen_q:
        errors.append(f"{where}: 题干重复: {q[:30]}")
    seen_q.add(q)
    opts = it["opts"]
    if not isinstance(opts, list) or len(opts) != 4:
        errors.append(f"{where}: 选项数≠4: {q[:20]}")
        return
    cleaned = []
    for i, o in enumerate(opts):
        o = str(o).strip()
        if not o:
            errors.append(f"{where}: 选项{i}为空: {q[:20]}")
            return
        if len(o) > 20:
            errors.append(f"{where}: 选项{i}超长({len(o)}): {q[:20]}")
        bc = bad_chars(o)
        if bc:
            errors.append(f"{where}: 选项{i}含非法字符 {bc}: {q[:20]}")
        cleaned.append(o)
    if len(set(cleaned)) != 4:
        errors.append(f"{where}: 选项有重复: {q[:20]} -> {cleaned}")
    ans = it["ans"]
    if not (0 <= ans <= 3):
        errors.append(f"{where}: ans 非法 {ans}: {q[:20]}")
        return
    big = str(it.get("big") or "").strip()
    bc = bad_chars(big)
    if bc:
        errors.append(f"{where}: 大字含非法字符 {bc}: {q[:20]}")
    src = str(it["src"]).strip()
    if not src:
        errors.append(f"{where}: src 为空: {q[:20]}")
    return {"q": q, "opts": cleaned, "ans": ans, "big": big, "src": src}


def main():
    jsonl_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "exam"
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "dist" / "csv_exam"

    errors, warnings = [], []
    banks = {}  # (subject, grade) -> [items]
    regions = {}  # subject -> set of region labels
    for subject in SUBJECTS:
        f = jsonl_dir / f"webq_{subject}.jsonl"
        if not f.exists():
            errors.append(f"缺少文件: {f}")
            continue
        seen_q = set()
        for lineno, line in enumerate(f.read_text(encoding="utf-8-sig").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                it = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"{subject} 第{lineno}行 JSON 解析失败: {e}")
                continue
            grade = it.get("grade")
            item = validate_item(it, subject, grade, errors, seen_q)
            if item is None:
                continue
            banks.setdefault((subject, grade), []).append(item)
            regions.setdefault(subject, set()).add(it["src"])

    # 题量检查
    total = 0
    for subject in SUBJECTS:
        for g in GRADES:
            n = len(banks.get((subject, g), []))
            total += n
            if n < TARGET_PER_GRADE:
                warnings.append(f"{SUBJECTS[subject]} g{g}: 仅 {n} 题（目标 {TARGET_PER_GRADE}）")

    if errors:
        print(f"共 {len(errors)} 个错误：")
        for e in errors[:80]:
            print("  [ERR]", e)
        if len(errors) > 80:
            print(f"  …另有 {len(errors)-80} 个")
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    stats = []
    for subject in SUBJECTS:
        for g in GRADES:
            items = banks.get((subject, g), [])
            if not items:
                continue
            lines = ["题干,选项A,选项B,选项C,选项D,答案,大字"]
            dist = [0, 0, 0, 0]
            for it in items:
                o = it["opts"]
                lines.append(f"{it['q']},{o[0]},{o[1]},{o[2]},{o[3]},{LETTERS[it['ans']]},{it['big']}")
                dist[it["ans"]] += 1
            path = out_dir / f"{subject}_g{g}.csv"
            path.write_bytes(("\ufeff" + "\r\n".join(lines) + "\r\n").encode("utf-8"))
            stats.append((path.name, len(items), dist))

    print(f"OK 共 {total} 题，生成 {len(stats)} 个 CSV -> {out_dir}")
    for name, n, dist in stats:
        print(f"  {name}: {n} 题  答案分布 A/B/C/D = {dist}")
    print("来源覆盖：")
    for subject in SUBJECTS:
        regs = sorted(regions.get(subject, []))
        print(f"  {SUBJECTS[subject]}（{len(regs)} 种来源）:")
        for r in regs:
            print(f"    - {r}")
    for w in warnings:
        print("  [WARN]", w)
    # 导入器自检：模拟 Harmony 朴素解析
    print("模拟 Harmony importCsv 朴素解析…")
    fail = 0
    for name, *_ in stats:
        for i, raw in enumerate((out_dir / name).read_text(encoding="utf-8-sig").split("\r\n")):
            if not raw.strip() or raw.startswith("题干"):
                continue
            c = raw.split(",")
            if len(c) != 7 or not c[0].strip() or c[5].strip().upper() not in LETTERS:
                print(f"  [ERR] {name} 第{i}行列数/答案非法: {raw[:40]}")
                fail += 1
    print("朴素解析自检：" + ("全部通过" if fail == 0 else f"{fail} 行失败"))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
