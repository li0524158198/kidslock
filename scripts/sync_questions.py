#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""题库单一源同步/校验。

仓库内唯一可编辑的题库文件是 data/questions.json（上游生成器：
scripts/gen_question_banks.py）。三平台资源目录下的 questions.json
均为本脚本分发出来的副本，不要手改。

用法：
    python scripts/sync_questions.py          # 把 data/ 分发到三平台资源位
    python scripts/sync_questions.py --check  # 只校验一致性（提交前/CI 用，不一致退出码 1）
"""
import argparse
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'data' / 'questions.json'

# 三平台资源位（分发目标）
DESTS = [
    ROOT / 'kidslock-src' / 'app' / 'src' / 'main' / 'res' / 'raw' / 'questions.json',
    ROOT / 'harmony' / 'KidsLock' / 'entry' / 'src' / 'main' / 'resources' / 'rawfile' / 'questions.json',
    ROOT / 'ios' / 'KidsLock' / 'KidsLock' / 'questions.json',
]


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description='题库单一源同步/校验')
    parser.add_argument('--check', action='store_true', help='只校验，不复制；不一致时退出码 1')
    args = parser.parse_args()

    if not SOURCE.is_file():
        print(f'FAIL | 单一源不存在: {SOURCE.relative_to(ROOT)}')
        return 1

    src_md5 = md5(SOURCE)
    print(f'单一源 data/questions.json  md5={src_md5}  ({SOURCE.stat().st_size} bytes)')

    drift = []
    for dest in DESTS:
        rel = dest.relative_to(ROOT)
        if not dest.is_file():
            drift.append(rel)
            print(f'MISSING | {rel}')
            continue
        if md5(dest) == src_md5:
            print(f'OK      | {rel}')
        else:
            drift.append(rel)
            print(f'DRIFT   | {rel}  md5={md5(dest)}')

    if args.check:
        if drift:
            print(f'\n校验失败：{len(drift)} 处副本与单一源不一致。'
                  f'请编辑 data/questions.json 后运行 python scripts/sync_questions.py 重新分发'
                  f'（不要直接改平台副本）。')
            return 1
        print('\n校验通过：三平台副本与单一源完全一致。')
        return 0

    for rel in drift:
        dest = ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE, dest)
        print(f'UPDATED | 已分发 → {rel}')
    if not drift:
        print('所有副本已是最新，无需分发。')
    else:
        print(f'\n已把 {len(drift)} 处副本同步为单一源内容。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
