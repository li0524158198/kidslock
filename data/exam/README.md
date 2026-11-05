# 小学语数英真题源数据（webq_*.jsonl）

全国各地 2022-2025 年期中期末真题改编的四选一单选题库，**已由
`scripts/gen_question_banks.py` 并入内置题库**（data/questions.json 的
chinese/math/english g1-g6 各年级库），随三平台构建分发。

## 文件

- `webq_chinese.jsonl` / `webq_math.jsonl` / `webq_english.jsonl`：各 180 行，每行一题
- 行格式：`{"grade": 1, "q": "9+8=?", "opts": ["17","18","16","15"], "ans": 0, "big": "", "src": "2023·北京海淀期末（改编）"}`
- `src` 字段为题目来源标注，仅供溯源，**不进入内置题库**

## 并入规则

- 追加到对应年级内置库末尾（固定顺序，重跑生成结果字节级一致）
- **题干与库内已有题目重复时跳过**（教材知识点自然重叠，如反义词/古诗/作者——
  同题干不同干扰项的变体题价值低）：实测跳过 7 处（语文 g1×4、g3×2、g6×1），
  实际并入 533/540 题
- 生成时打印全部跳过明细；并入后由 `qa/bank_audit.py` 复核同库唯一性

## 相关工具

- `python scripts/gen_question_banks.py` 重新生成（含真题合并）
- `python scripts/build_exam_csv.py` 从本目录导出 18 个真题 CSV（`dist/csv_exam/`，
  供旧版本 App 手动导入；真题已内置，CSV 非必需）
