#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发布清单核对脚本（测试报告 P1-3/P1-4 的流程性建议）。

核对项：
  R1  单一源 data/questions.json 与三平台副本 MD5 一致（Android res/raw / 鸿蒙 rawfile / iOS 源目录）
  R2  dist/csv 36 个种子与 questions.json 逐题一致（支持引号 CSV）
  R3  dist release APK 内嵌 questions.json 与源码一致
  R4  dist HAP 内含 questions.json 且与源码一致
  R5  download-site/assets 的 APK/HAP 与 dist 产物 MD5 一致
  R6  dist/kidslock-download-site.zip 内的 APK 与 dist 一致（防 zip 过期）
  R7  APK 版本号（需 build-tools aapt，存在时才检查）

用法：python qa/release_check.py
退出码 0 = 全部通过；1 = 存在 FAIL。
"""
import csv
import hashlib
import io
import json
import os
import sys
import zipfile

from qaenv import ROOT as _ROOT_ENV
ROOT = str(_ROOT_ENV)
# 单一源 + 三平台副本一并核对（R1）
JSON_PATHS = [
    f"{ROOT}/data/questions.json",
    f"{ROOT}/kidslock-src/app/src/main/res/raw/questions.json",
    f"{ROOT}/harmony/KidsLock/entry/src/main/resources/rawfile/questions.json",
    f"{ROOT}/ios/KidsLock/KidsLock/questions.json",
]
APK_DIST = f"{ROOT}/dist/kidslock-release-universal.apk"
HAP_DIST = f"{ROOT}/dist/entry-default-unsigned.hap"
SITE_APK_DIR = f"{ROOT}/download-site/assets"
SITE_ZIP = f"{ROOT}/dist/kidslock-download-site.zip"
CSV_DIR = f"{ROOT}/dist/csv"
AAPT_CANDIDATES = [
    f"{ROOT}/tools/android-sdk/build-tools/34.0.0/aapt.exe",
    f"{ROOT}/tools/android-sdk/build-tools/34.0.0/aapt",
]

_p = _f = 0


def check(name, ok, detail=""):
    global _p, _f
    print(("PASS | " if ok else "FAIL | ") + name + ((" | " + detail) if detail else ""))
    if ok:
        _p += 1
    else:
        _f += 1


def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_bytes(b):
    return hashlib.md5(b).hexdigest()


def zip_find_entry(zf, suffix):
    for n in zf.namelist():
        if n.endswith(suffix):
            return n
    return None


def main():
    # R1 三平台 questions.json 一致
    src_md5 = md5_file(JSON_PATHS[0])
    bad = [p for p in JSON_PATHS[1:] if md5_file(p) != src_md5]
    check("R1 单一源+三平台 questions.json MD5 一致", not bad, f"{src_md5[:10]}…")

    data = json.load(open(JSON_PATHS[0], encoding="utf-8"))

    # R2 dist/csv 与 JSON 逐题一致（csv 模块按 RFC4180 解析，兼容引号包裹）
    mismatch = []
    for bank, items in data["banks"].items():
        path = os.path.join(CSV_DIR, f"{bank}.csv")
        if not os.path.exists(path):
            mismatch.append(f"{bank}: CSV 缺失")
            continue
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        rows = [r for r in rows if r and any(c.strip() for c in r)]
        if rows and rows[0] and "题干" in rows[0][0]:
            rows = rows[1:]
        if len(rows) != len(items):
            mismatch.append(f"{bank}: {len(rows)} 行 ≠ {len(items)} 题")
            continue
        for r, it in zip(rows, items):
            q = r[0]
            opts = r[1:5]
            ans_letter = r[5] if len(r) > 5 else ""
            big = r[6] if len(r) > 6 else ""
            ans = "ABCD".index(ans_letter) if ans_letter in "ABCD" else 0
            want_big = it.get("char") or ""
            if q != it["q"] or opts != it["opts"] or ans != it["ans"] or big != want_big:
                mismatch.append(f"{bank}: 题干/选项/答案与 JSON 不一致（{q[:20]}…）")
                break
    check("R2 dist/csv 36 库与 JSON 逐题一致", not mismatch, "; ".join(mismatch[:3]))

    # R3 APK 内嵌 questions.json（release 包经 AAPT2 优化会重命名资源，按内容 MD5 全包扫描）
    if os.path.exists(APK_DIST):
        with zipfile.ZipFile(APK_DIST) as zf:
            hit = None
            for n in zf.namelist():
                try:
                    if md5_bytes(zf.read(n)) == src_md5:
                        hit = n
                        break
                except Exception:
                    continue
            check("R3 dist APK 内嵌 questions.json 与源码一致", hit is not None,
                  f"条目={hit}" if hit else "APK 内未找到与源码一致的 questions.json")
    else:
        check("R3 dist APK 内嵌 questions.json", False, "dist APK 不存在")

    # R4 HAP 内含 questions.json（rawfile 保持原名）
    if os.path.exists(HAP_DIST):
        with zipfile.ZipFile(HAP_DIST) as zf:
            entry = zip_find_entry(zf, "rawfile/questions.json") or zip_find_entry(zf, "questions.json")
            if entry is None:
                check("R4 dist HAP 内含 questions.json 与源码一致", False, "HAP 内未找到 questions.json（旧包？）")
            else:
                embedded = md5_bytes(zf.read(entry))
                check("R4 dist HAP 内含 questions.json 与源码一致", embedded == src_md5,
                      f"hap={embedded[:10]}… src={src_md5[:10]}…")
    else:
        check("R4 dist HAP 内含 questions.json", False, "dist HAP 不存在")

    # R5 download-site/assets 与 dist 一致
    apk_md5 = md5_file(APK_DIST) if os.path.exists(APK_DIST) else None
    hap_md5 = md5_file(HAP_DIST) if os.path.exists(HAP_DIST) else None
    site_apks = [f for f in os.listdir(SITE_APK_DIR) if f.endswith(".apk")] if os.path.isdir(SITE_APK_DIR) else []
    site_ok, site_detail = True, []
    if len(site_apks) != 1:
        site_ok = False
        site_detail.append(f"assets 内 APK 数量 {len(site_apks)}（应恰好 1 个）: {site_apks}")
    for f in site_apks:
        m = md5_file(os.path.join(SITE_APK_DIR, f))
        if m != apk_md5:
            site_ok = False
            site_detail.append(f"{f} 与 dist APK 不一致")
    site_hap = os.path.join(SITE_APK_DIR, "entry-default-unsigned.hap")
    if os.path.exists(site_hap):
        if hap_md5 and md5_file(site_hap) != hap_md5:
            site_ok = False
            site_detail.append("assets HAP 与 dist HAP 不一致")
    else:
        site_ok = False
        site_detail.append("assets 缺少 entry-default-unsigned.hap")
    check("R5 download-site/assets 与 dist 产物一致", site_ok, "; ".join(site_detail[:3]))

    # R6 下载站 zip 内 APK 与 dist 一致
    if os.path.exists(SITE_ZIP):
        with zipfile.ZipFile(SITE_ZIP) as zf:
            apks = [n for n in zf.namelist() if n.endswith(".apk")]
            if not apks:
                check("R6 下载站 zip 内 APK 与 dist 一致", False, "zip 内无 APK")
            elif len(apks) > 1:
                check("R6 下载站 zip 内 APK 与 dist 一致", False, f"zip 内多个 APK: {apks}")
            else:
                zmd5 = md5_bytes(zf.read(apks[0]))
                check("R6 下载站 zip 内 APK 与 dist 一致", apk_md5 and zmd5 == apk_md5, apks[0])
    else:
        check("R6 下载站 zip 内 APK 与 dist 一致", False, "zip 不存在")

    # R7 APK 版本号（aapt 可用时）
    aapt = next((p for p in AAPT_CANDIDATES if os.path.exists(p)), None)
    if aapt and os.path.exists(APK_DIST):
        out = os.popen(f'"{aapt}" dump badging "{APK_DIST}"').read()
        line = next((l for l in out.splitlines() if l.startswith("package:")), "")
        expect_vc, expect_vn = "versionCode='6'", "versionName='1.5.1'"
        check("R7 APK 版本号 versionCode=6 / versionName=1.5.1",
              expect_vc in line and expect_vn in line, line[:80])
    else:
        print("SKIP | R7 APK 版本号（未找到 aapt）")

    print(f"\n===== 发布核对: {_p} PASS / {_f} FAIL =====")
    sys.exit(1 if _f else 0)


if __name__ == "__main__":
    main()
