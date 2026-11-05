@echo off
rem ============================================================
rem KidsLock Android 模拟器一键运行脚本
rem 修复：多模拟器在线时 adb 必须带 -s（否则 more than one device
rem 导致启动等待死循环）；AVD 已在线时直接复用，不再重复启动
rem ============================================================
setlocal enabledelayedexpansion
set SDK=D:\project\kidslock\tools\android-sdk
set ADB=%SDK%\platform-tools\adb.exe
set APK=D:\project\kidslock\dist\kidslock-release-universal.apk
set AVD=KidsLockMini

if not exist "%SDK%\emulator\emulator.exe" (
  echo [错误] 找不到模拟器
  pause & exit /b 1
)
if not exist "%APK%" (
  echo [错误] 找不到 APK: %APK%
  pause & exit /b 1
)

rem ---- 探测该 AVD 是否已在线（复用，不重复启动）----
call :findserial
if defined SERIAL (
  echo [1/5] %AVD% 已在线（%SERIAL%），直接复用
  goto positioned
)

echo [1/5] 启动模拟器...
start "" "%SDK%\emulator\emulator.exe" -avd %AVD% -netdelay none -netspeed full -no-boot-anim

echo       等待模拟器出现在 adb（最长 120 秒）...
set /a TRIES=0
:waitserial
ping -n 3 127.0.0.1 >nul
set /a TRIES+=1
call :findserial
if not defined SERIAL if %TRIES% LSS 40 goto waitserial
if not defined SERIAL (
  echo [错误] 模拟器 120 秒内未出现在 adb
  pause & exit /b 1
)
echo       序列号: %SERIAL%

echo [2/5] 等待窗口出现并定位到屏幕内...
set /a TRIES=0
:waitwin
ping -n 3 127.0.0.1 >nul
set /a TRIES+=1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix-emulator-window.ps1" -AvdName %AVD% >nul 2>&1
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
"%ADB%" -s %SERIAL% shell getprop sys.boot_completed 2>nul | findstr "1" >nul
if not errorlevel 1 goto bootok
if %WAITED% GEQ 240 (
  echo [错误] 模拟器 4 分钟内未完成启动
  pause & exit /b 1
)
goto waitboot

:bootok
echo [4/5] 安装 APK...
"%ADB%" -s %SERIAL% install -r "%APK%"

echo [5/5] 启动应用...
"%ADB%" -s %SERIAL% shell am start -n com.kidslock.app/.MainActivity

echo.
echo 完成！%AVD%（%SERIAL%）已就绪，窗口固定在屏幕左上角。
echo.
pause
endlocal
exit /b 0

rem ---- 子过程：遍历在线模拟器，找到 AVD 对应序列号 → SERIAL ----
rem （avd name 输出行尾带 CR，直接字符串比较永不相等 → 用 findstr /b 前缀匹配）
:findserial
set SERIAL=
"%ADB%" devices > "%TEMP%\kl_adb_devices.txt" 2>nul
for /f "usebackq tokens=1" %%D in (`findstr /r /c:"^emulator-" "%TEMP%\kl_adb_devices.txt"`) do (
  "%ADB%" -s %%D emu avd name > "%TEMP%\kl_avd_name.txt" 2>nul
  findstr /i /b /c:"%AVD%" "%TEMP%\kl_avd_name.txt" >nul 2>&1
  if not errorlevel 1 set SERIAL=%%D
)
goto :eof
