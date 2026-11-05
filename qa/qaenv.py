#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qa 冒烟脚本公共环境：仓库根 / adb / 设备序列号 / 题库 JSON 的统一入口。

所有路径从本文件位置推导（仓库根 = qa/ 的上一级），换机器无需改代码。
可用环境变量覆盖：
    KIDSLOCK_ADB     adb 可执行文件路径。默认优先用仓库 tools/android-sdk/ 里的，
                     不存在则回退到 PATH 里的 adb。
    KIDSLOCK_SERIAL  设备/模拟器序列号（默认 emulator-5554）。
"""
import json
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 题库单一源（三平台副本由 scripts/sync_questions.py 保证一致）
QUESTIONS_JSON = ROOT / 'data' / 'questions.json'


def adb() -> str:
    """adb 可执行文件：环境变量 > 仓库 tools 内置 > PATH。"""
    env = os.environ.get('KIDSLOCK_ADB')
    if env:
        return env
    exe = 'adb.exe' if os.name == 'nt' else 'adb'
    local = ROOT / 'tools' / 'android-sdk' / 'platform-tools' / exe
    if local.exists():
        return str(local)
    return shutil.which('adb') or exe  # 都没有时交给 subprocess 报 FileNotFound


SERIAL = os.environ.get('KIDSLOCK_SERIAL', 'emulator-5554')

# 临时目录（uiautomator dump 拉取用；str 类型，脚本里有 TMP + '/xxx' 拼接）
TMP = tempfile.gettempdir()


def load_questions() -> dict:
    """加载题库单一源。"""
    return json.load(open(QUESTIONS_JSON, encoding='utf-8'))
