#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键构建 + 发布卡点（第二轮复测 N-1 建议落地）。

流程（任一步失败立即中止，产物与源码不一致时禁止发布）：
  1. python scripts/sync_questions.py --check    # 题库单一源一致性
  2. Android  gradle assembleDebug assembleRelease（需 JDK 17+）
  3. Harmony  hvigor assembleHap（需 node 18+ + OpenHarmony SDK）
  4. 部署 dist/ + download-site/assets/ + 重建下载站 zip
  5. 发布卡点：qa/test_data.py + qa/release_check.py 必须全绿

用法：
  python scripts/build_all.py
  python scripts/build_all.py --skip-harmony    # 无鸿蒙 SDK 环境时只构建 Android
  python scripts/build_all.py --skip-android
  python scripts/build_all.py --deploy-only     # 产物已构建好，只做部署+卡点

环境自动探测（均可用同名环境变量覆盖）：
  JAVA_HOME        默认探测 C:/java/jdk-21.0.7
  gradle           默认 tools/gradle-8.5/bin
  DEVECO_SDK_HOME  默认 tools/ohos-sdk-home/sdk
  node             从 PATH 取
iOS 无法在本机构建：推 GitHub 后用 Actions 云编译（产物核对以 qa/release_check.py 为准）。
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def die(msg: str) -> None:
    print(f'\n[ABORT] {msg}')
    sys.exit(1)


def run(title: str, cmd, cwd: Path = None, env_extra: dict = None, tail: int = 6) -> None:
    """跑子进程：失败打印输出尾部并中止。"""
    print(f'\n===== {title} =====')
    env = os.environ.copy()
    if env_extra:
        env.update({k: str(v) for k, v in env_extra.items()})
    r = subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None, env=env)
    if r.returncode != 0:
        die(f'{title} 失败（exit {r.returncode}）')


def jdk_major(p: Path) -> int:
    rel = p / 'release'
    if rel.is_file():
        m = re.search(r'JAVA_VERSION="(\d+)', rel.read_text(encoding='utf-8', errors='ignore'))
        if m:
            return int(m.group(1))
    return -1


def detect_java() -> Path:
    """JDK 17+：环境变量优先，但版本不够（如系统 JAVA_HOME=JDK8）时跳过用本机 JDK21。"""
    cands = []
    v = os.environ.get('JAVA_HOME')
    if v:
        cands.append(Path(v))
    cands += [Path('C:/java/jdk-21.0.7'), Path('C:/Program Files/Java/jdk-21'),
              Path('C:/Program Files/Java/jdk-17'), ROOT / 'tools' / 'jdk-21.0.7']
    for c in cands:
        if c.is_dir() and jdk_major(c) >= 17:
            return c
    die(f'未找到 JDK 17+（AGP 8.2 需要；当前 JAVA_HOME={v}）')


def detect_gradle() -> Path:
    v = os.environ.get('GRADLE_HOME')
    if v:
        g = Path(v) / 'bin'
        if g.is_dir():
            return g
    g = ROOT / 'tools' / 'gradle-8.5' / 'bin'
    if g.is_dir():
        return g
    die('未找到 gradle：请设置 GRADLE_HOME 或提供 tools/gradle-8.5')


def detect_sdk() -> Path:
    v = os.environ.get('DEVECO_SDK_HOME')
    if v:
        return Path(v)
    p = ROOT / 'tools' / 'ohos-sdk-home' / 'sdk'
    if p.is_dir():
        return p
    die('未找到 OpenHarmony SDK：请设置 DEVECO_SDK_HOME（组装见 tools/setup-ohos-sdk.py）')


def version_name() -> str:
    gradle = (ROOT / 'kidslock-src' / 'app' / 'build.gradle').read_text(encoding='utf-8')
    m = re.search(r'versionName\s+"([^"]+)"', gradle)
    return m.group(1) if m else 'unknown'


def deploy(ver: str) -> None:
    print(f'\n===== 部署产物（v{ver}）=====')
    rel = ROOT / 'kidslock-src' / 'app' / 'build' / 'outputs' / 'apk' / 'release' / 'app-universal-release.apk'
    dbg = ROOT / 'kidslock-src' / 'app' / 'build' / 'outputs' / 'apk' / 'debug' / 'app-universal-debug.apk'
    hap = ROOT / 'harmony' / 'KidsLock' / 'entry' / 'build' / 'default' / 'outputs' / 'default' / 'entry-default-unsigned.hap'
    for f in (rel, dbg, hap):
        if not f.is_file():
            die(f'缺少构建产物: {f.relative_to(ROOT)}')
    dist = ROOT / 'dist'
    shutil.copyfile(rel, dist / 'kidslock-release-universal.apk')
    shutil.copyfile(dbg, dist / 'kidslock-debug-universal.apk')
    shutil.copyfile(hap, dist / 'entry-default-unsigned.hap')

    # 下载站资产（APK 用带版本号文件名；清掉旧版本文件）
    assets = ROOT / 'download-site' / 'assets'
    assets.mkdir(parents=True, exist_ok=True)
    apk_name = f'kidslock-v{ver}.apk'
    for old in assets.glob('kidslock-v*.apk'):
        if old.name != apk_name:
            old.unlink()
            print(f'  移除旧版本资产: {old.name}')
    shutil.copyfile(rel, assets / apk_name)
    shutil.copyfile(hap, assets / 'entry-default-unsigned.hap')

    # 重建下载站 zip（保持既有内部结构 kidslock-download/…）
    site_files = ['index.html', 'kidslock-download.service', 'server.py', '部署说明.md',
                  'assets/icon.png', f'assets/{apk_name}', 'assets/entry-default-unsigned.hap']
    zpath = dist / 'kidslock-download-site.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in site_files:
            src = ROOT / 'download-site' / f
            if not src.is_file():
                die(f'下载站缺文件: {f}')
            z.write(src, f'kidslock-download/{f}')
    print(f'  dist/ 与 download-site/assets/ 已更新；zip 重建 {zpath.name}（{zpath.stat().st_size} bytes）')


def main() -> int:
    ap = argparse.ArgumentParser(description='KidsLock 一键构建 + 发布卡点')
    ap.add_argument('--skip-android', action='store_true')
    ap.add_argument('--skip-harmony', action='store_true')
    ap.add_argument('--deploy-only', action='store_true')
    args = ap.parse_args()

    # 1. 题库一致性
    run('题库单一源校验', [sys.executable, ROOT / 'scripts' / 'sync_questions.py', '--check'])

    if not args.deploy_only:
        # 2. Android
        if not args.skip_android:
            java = detect_java()
            gradle_bin = detect_gradle() / ('gradle.bat' if os.name == 'nt' else 'gradle')
            run(f'Android APK（JAVA_HOME={java}）',
                ['cmd', '/c', gradle_bin, 'assembleDebug', 'assembleRelease', '--console=plain'],
                cwd=ROOT / 'kidslock-src', env_extra={'JAVA_HOME': java})
        # 3. Harmony
        if not args.skip_harmony:
            sdk = detect_sdk()
            node = shutil.which('node') or die('PATH 里没有 node（hvigor 需要 Node 18+）')
            run(f'鸿蒙 HAP（DEVECO_SDK_HOME={sdk}）',
                [node, 'node_modules/@ohos/hvigor/bin/hvigor.js', 'assembleHap',
                 '--mode', 'module', '-p', 'product=default', '--no-daemon'],
                cwd=ROOT / 'harmony' / 'KidsLock', env_extra={'DEVECO_SDK_HOME': sdk})

    # 4. 部署
    ver = version_name()
    deploy(ver)

    # 5. 发布卡点（失败即中止发布）
    run('卡点 T1/T2 数据层', [sys.executable, ROOT / 'qa' / 'test_data.py'])
    run('卡点 R1-R7 发布核对', [sys.executable, ROOT / 'qa' / 'release_check.py'])

    print(f'''
============================================================
 构建完成且全部卡点通过：v{ver}
   dist/kidslock-release-universal.apk
   dist/kidslock-debug-universal.apk
   dist/entry-default-unsigned.hap
   dist/kidslock-download-site.zip
 iOS：推 GitHub 后 Actions 云编译（本机无法构建）
============================================================''')
    return 0


if __name__ == '__main__':
    sys.exit(main())
