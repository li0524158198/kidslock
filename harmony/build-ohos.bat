@echo off
rem ============================================================
rem KidsLock HarmonyOS 本地命令行编译脚本（实测通过）
rem 前置条件：
rem   1. Node.js 18+ 已安装
rem   2. 已按 tools/setup-ohos-sdk.py 组装好 OpenHarmony SDK
rem      （结构：<SDK根>\toolchains\openharmony\<组件> + hms\<组件>）
rem   3. 设置环境变量 DEVECO_SDK_HOME 指向 <SDK根>
rem 用法：
rem   build-ohos.bat            编译 debug HAP
rem   build-ohos.bat release    编译 release HAP
rem 产物：
rem   KidsLock\entry\build\default\outputs\default\entry-default-unsigned.hap
rem ============================================================
setlocal
cd /d "%~dp0KidsLock"

if "%DEVECO_SDK_HOME%"=="" (
  echo [错误] 未设置 DEVECO_SDK_HOME 环境变量
  echo 请先运行: python tools\setup-ohos-sdk.py ^<SDK组件目录^> ^<SDK根目录^>
  exit /b 1
)

if "%~1"=="release" (
  node node_modules\@ohos\hvigor\bin\hvigor.js assembleHap --mode module -p product=default -p buildMode=release --no-daemon
) else (
  node node_modules\@ohos\hvigor\bin\hvigor.js assembleHap --mode module -p product=default --no-daemon
)

endlocal
