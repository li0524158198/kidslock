@echo off
rem ============================================================
rem KidsLock phone emulator one-click launcher (window auto-positioned)
rem NOTE: keep this file ASCII-only. Chinese comments/echo break
rem parsing under a GBK (cp936) console - the script would abort.
rem Fixes: detect+reuse an already-online AVD (no duplicate start);
rem all adb calls use -s SERIAL (with two emulators online, a bare
rem "adb shell" fails with "more than one device" and the boot wait
rem used to hang for 4 minutes).
rem ============================================================
setlocal enabledelayedexpansion
set SDK=D:\project\kidslock\tools\android-sdk
set ADB=%SDK%\platform-tools\adb.exe
set APK=D:\project\kidslock\dist\kidslock-release-universal.apk
set AVD=KidsLockMini

if not exist "%SDK%\emulator\emulator.exe" (
  echo [ERROR] emulator not found
  pause & exit /b 1
)
if not exist "%APK%" (
  echo [ERROR] APK not found: %APK%
  pause & exit /b 1
)

call :findserial
if defined SERIAL (
  echo [1/5] %AVD% already online [%SERIAL%], reusing
  goto positioned
)

echo [1/5] Starting emulator...
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

echo [2/5] Waiting for window, positioning on screen...
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
echo       Window positioned (20,20)
echo [3/5] Waiting for boot (max 4 min)...
set /a WAITED=0
:waitboot
ping -n 6 127.0.0.1 >nul
set /a WAITED+=5
"%ADB%" -s %SERIAL% shell getprop sys.boot_completed 2>nul | findstr "1" >nul
if not errorlevel 1 goto bootok
if %WAITED% GEQ 240 (
  echo [ERROR] emulator did not finish booting within 4 minutes
  pause & exit /b 1
)
goto waitboot

:bootok
echo [4/5] Installing APK...
"%ADB%" -s %SERIAL% install -r "%APK%"

echo [5/5] Launching app...
"%ADB%" -s %SERIAL% shell am start -n com.kidslock.app/.MainActivity

echo.
echo Done: %AVD% (%SERIAL%) is ready, window pinned top-left.
echo.
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
