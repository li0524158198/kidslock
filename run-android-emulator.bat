@echo off
rem ============================================================
rem KidsLock Android 模拟器一键运行脚本（本机实测通过）
rem 前置：已完成工具链安装（D:\project\kidslock\tools\android-sdk）
rem 用法：直接双击或命令行运行本脚本
rem 说明：窗口缩放 0.35，适配 1536x960 笔记本屏幕完整显示
rem ============================================================
setlocal
set SDK=D:\project\kidslock\tools\android-sdk
set ADB=%SDK%\platform-tools\adb.exe
set APK=D:\project\kidslock\dist\kidslock-release-universal.apk

if not exist "%SDK%\emulator\emulator.exe" (
  echo [错误] 找不到模拟器: %SDK%\emulator\emulator.exe
  pause
  exit /b 1
)
if not exist "%APK%" (
  echo [错误] 找不到 APK: %APK%
  pause
  exit /b 1
)

echo [1/4] 启动模拟器（首次冷启动约 1-2 分钟）...
start "" "%SDK%\emulator\emulator.exe" -avd KidsLock -netdelay none -netspeed full -no-boot-anim -scale 0.35

echo [2/4] 等待系统启动完成（最长 4 分钟）...
set /a WAITED=0
:waitboot
ping -n 6 127.0.0.1 >nul
set /a WAITED+=5
"%ADB%" shell getprop sys.boot_completed 2>nul | findstr "1" >nul
if not errorlevel 1 goto bootok
if %WAITED% GEQ 240 (
  echo [错误] 模拟器 4 分钟内未完成启动，请查看模拟器窗口状态后重试
  pause
  exit /b 1
)
goto waitboot

:bootok
echo [3/4] 安装 APK...
"%ADB%" install -r "%APK%"

echo [4/4] 启动应用...
"%ADB%" shell am start -n com.kidslock.app/.MainActivity

echo.
echo 完成！模拟器窗口中已运行「儿童锁屏」。
echo 提示：锁屏界面为电视版布局，如需完整显示选项按钮可执行：
echo   adb shell wm density 160   （恢复用 wm density reset）
echo.
pause
endlocal
