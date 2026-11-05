@echo off
rem ============================================================
rem KidsLock TV 模拟器一键启动（窗口自动定位到屏幕内）
rem 修复：不再硬编码 emulator-5556（序列号取决于启动顺序），
rem 改为按 AVD 名动态探测；AVD 已在线时直接复用
rem ============================================================
setlocal enabledelayedexpansion
set SDK=D:\project\kidslock\tools\android-sdk
set ADB=%SDK%\platform-tools\adb.exe
set APK=D:\project\kidslock\dist\kidslock-release-universal.apk
set AVD=KidsLockTV720

call :findserial
if defined SERIAL (
  echo [1/4] %AVD% 已在线（%SERIAL%），直接复用
  goto positioned
)

echo [1/4] 启动 TV 模拟器...
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

echo [2/4] 等待窗口出现并定位...
set /a TRIES=0
:waitwin
ping -n 3 127.0.0.1 >nul
set /a TRIES+=1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix-emulator-window.ps1" -AvdName %AVD% -X 20 -Y 20 > "%TEMP%\fixwin_out.txt" 2>&1
findstr /c:"moved" "%TEMP%\fixwin_out.txt" >nul
if not errorlevel 1 goto positioned
if %TRIES% GEQ 20 goto positioned
goto waitwin

:positioned
echo       窗口已定位
echo [3/4] 等待系统启动（最长 5 分钟）...
set /a WAITED=0
:waitboot
ping -n 6 127.0.0.1 >nul
set /a WAITED+=5
"%ADB%" -s %SERIAL% shell getprop sys.boot_completed 2>nul | findstr "1" >nul
if not errorlevel 1 goto bootok
if %WAITED% GEQ 300 (
  echo [提示] 启动较慢，如窗口已显示可继续等待
  pause & exit /b 1
)
goto waitboot

:bootok
echo [4/4] 安装并启动应用...
"%ADB%" -s %SERIAL% install -r "%APK%"
"%ADB%" -s %SERIAL% shell appops set com.kidslock.app SYSTEM_ALERT_WINDOW allow
"%ADB%" -s %SERIAL% shell am start -n com.kidslock.app/.MainActivity
echo.
echo 完成！%AVD%（%SERIAL%）已就绪。
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
