#!/usr/bin/env sh
# KidsLock JVM 逻辑回归：用 Android shims 把真实生产源码（PrefManager/QuestionBank）
# 编译到桌面 JVM 上跑测试。无需 Android 设备/SDK。
#
# 用法：
#   qa/jvm/run.sh          跑 JvmTests（主回归：题库引擎 + 状态机）
#   qa/jvm/run.sh csv      跑 CsvMatrix（跨平台 CSV 矩阵，M4 需先有鸿蒙侧导出）
set -e

JVMDIR=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$JVMDIR/../.." && pwd)

command -v javac >/dev/null 2>&1 || { echo '[ERROR] PATH 里没有 javac，需要 JDK 8 或更高版本。'; exit 1; }

OUT="$JVMDIR/out"
CP="$JVMDIR/vendor/org.json.jar"
mkdir -p "$OUT"

javac -encoding UTF-8 -d "$OUT" -cp "$CP" \
  "$JVMDIR"/shims/android/app/*.java \
  "$JVMDIR"/shims/android/content/*.java \
  "$JVMDIR"/shims/android/content/pm/*.java \
  "$JVMDIR"/shims/android/content/res/*.java \
  "$JVMDIR"/shims/android/util/*.java \
  "$JVMDIR"/shims/com/kidslock/app/*.java \
  "$ROOT/kidslock-src/app/src/main/java/com/kidslock/app/PrefManager.java" \
  "$ROOT/kidslock-src/app/src/main/java/com/kidslock/app/QuestionBank.java" \
  "$JVMDIR"/src/*.java

MAIN=JvmTests
if [ "$1" = "csv" ]; then
    MAIN=CsvMatrix
fi

java -cp "$OUT:$CP" "-Dkidslock.root=$ROOT" "-Dkidslock.filedir=$JVMDIR/filedir" "$MAIN"
