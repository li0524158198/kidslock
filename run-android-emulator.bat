@echo off
rem ============================================================
rem KidsLock Android 模拟器一键运行脚本
rem 启动后自动把窗口强制定位到屏幕内（不依赖会被覆写的 ini）
rem ============================================================
setlocal
set SDK=D:\project\kidslock\tools\android-sdk
set ADB=%SDK%\platform-tools\adb.exe
set APK=D:\project\kidslock\dist\kidslock-release-universal.apk

if not exist "%SDK%\emulator\emulator.exe" (
  echo [错误] 找不到模拟器
  pause & exit /b 1
)
if not exist "%APK%" (
  echo [错误] 找不到 APK: %APK%
  pause & exit /b 1
)

echo [1/5] 启动模拟器...
start "" "%SDK%\emulator\emulator.exe" -avd KidsLockMini -netdelay none -netspeed full -no-boot-anim

echo [2/5] 等待窗口出现并定位到屏幕内...
set /a TRIES=0
:waitwin
ping -n 3 127.0.0.1 >nul
set /a TRIES+=1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix-emulator-window.ps1" -AvdName KidsLockMini >nul 2>&1
findstr /c:"moved" "%TEMP%\fixwin_out.txt" >nul 2>&1
if not errorlevel 1 goto positioned
if %TRIES% GEQ 20 goto positioned
goto waitwin

:positioned
echo       窗口已定位 (20,20)
echo [3/5] 等待系统启动（最长 4 分钟）...
set /a WAITED=0
:waitboot
ping -n 6 127.0.0.1 >nul
set /a WAITED+=5
"%ADB%" shell getprop sys.boot_completed 2>nul | findstr "1" >nul
if not errorlevel 1 goto bootok
if %WAITED% GEQ 240 (
  echo [错误] 模拟器 4 分钟内未完成启动
  pause & exit /b 1
)
goto waitboot

:bootok
echo [4/5] 安装 APK...
"%ADB%" install -r "%APK%"

echo [5/5] 启动应用...
"%ADB%" shell am start -n com.kidslock.app/.MainActivity

echo.
echo 完成！窗口已固定在屏幕左上角。
echo.
pause
endlocal
