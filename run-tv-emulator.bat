@echo off
rem ============================================================
rem KidsLock TV emulator one-click launcher (window auto-positioned)
rem NOTE: keep this file ASCII-only. Chinese comments/echo break
rem parsing under a GBK (cp936) console - the script would abort.
rem Fixes: detect+reuse an already-online AVD (no duplicate start);
rem never hardcode serials (emulator-5556 depends on start order);
rem all adb calls use -s SERIAL (multi-device otherwise errors out).
rem ============================================================
setlocal enabledelayedexpansion
set SDK=D:\project\kidslock\tools\android-sdk
set ADB=%SDK%\platform-tools\adb.exe
set APK=D:\project\kidslock\dist\kidslock-release-universal.apk
set AVD=KidsLockTV720

call :findserial
if defined SERIAL (
  echo [1/4] %AVD% already online [%SERIAL%], reusing
  goto positioned
)

echo [1/4] Starting TV emulator...
start "" "%SDK%\emulator\emulator.exe" -avd %AVD% -netdelay none -netspeed full -no-boot-anim

echo       Waiting for it to appear in adb (max 120s)...
set /a TRIES=0
:waitserial
ping -n 3 127.0.0.1 >nul
set /a TRIES+=1
call :findserial
if not defined SERIAL if %TRIES% LSS 40 goto waitserial
if not defined SERIAL (
  echo [ERROR] emulator did not appear in adb within 120s
  pause & exit /b 1
)
echo       Serial: %SERIAL%

echo [2/4] Waiting for window, positioning on screen...
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
echo       Window positioned
echo [3/4] Waiting for boot (max 5 min)...
set /a WAITED=0
:waitboot
ping -n 6 127.0.0.1 >nul
set /a WAITED+=5
"%ADB%" -s %SERIAL% shell getprop sys.boot_completed 2>nul | findstr "1" >nul
if not errorlevel 1 goto bootok
if %WAITED% GEQ 300 (
  echo [HINT] boot is slow; keep waiting if the window is visible
  pause & exit /b 1
)
goto waitboot

:bootok
echo [4/4] Installing and launching app...
"%ADB%" -s %SERIAL% install -r "%APK%"
"%ADB%" -s %SERIAL% shell appops set com.kidslock.app SYSTEM_ALERT_WINDOW allow
"%ADB%" -s %SERIAL% shell am start -n com.kidslock.app/.MainActivity
echo.
echo Done: %AVD% (%SERIAL%) is ready.
pause
endlocal
exit /b 0

rem ---- subroutine: find the serial of the online emulator whose
rem ---- AVD name matches ("emu avd name" output ends with CR, so
rem ---- compare via findstr /b prefix match, never string equality;
rem ---- go through temp files to avoid quoted-command-in-for pitfalls)
:findserial
set SERIAL=
"%ADB%" devices > "%TEMP%\kl_adb_devices.txt" 2>nul
for /f "usebackq tokens=1" %%D in (`findstr /r /c:"^emulator-" "%TEMP%\kl_adb_devices.txt"`) do (
  "%ADB%" -s %%D emu avd name > "%TEMP%\kl_avd_name.txt" 2>nul
  findstr /i /b /c:"%AVD%" "%TEMP%\kl_avd_name.txt" >nul 2>&1
  if not errorlevel 1 set SERIAL=%%D
)
goto :eof
