@echo off
rem KidsLock TV 模拟器一键启动（窗口自动定位到屏幕内）
setlocal
set SDK=D:\project\kidslock\tools\android-sdk
set ADB=%SDK%\platform-tools\adb.exe

echo [1/4] 启动 TV 模拟器...
start "" "%SDK%\emulator\emulator.exe" -avd KidsLockTV720 -netdelay none -netspeed full -no-boot-anim

echo [2/4] 等待窗口出现并定位...
set /a TRIES=0
:waitwin
ping -n 3 127.0.0.1 >nul
set /a TRIES+=1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix-emulator-window.ps1" -AvdName KidsLockTV720 -X 20 -Y 20 > "%TEMP%\fixwin_out.txt" 2>&1
findstr /c:"moved" "%TEMP%\fixwin_out.txt" >nul 2>&1
if not errorlevel 1 goto positioned
if %TRIES% GEQ 20 goto positioned
goto waitwin

:positioned
echo       窗口已定位
echo [3/4] 等待系统启动...
set /a WAITED=0
:waitboot
ping -n 6 127.0.0.1 >nul
set /a WAITED+=5
"%ADB%" -s emulator-5556 shell getprop sys.boot_completed 2>nul | findstr "1" >nul
if not errorlevel 1 goto bootok
if %WAITED% GEQ 300 (
  echo [提示] 启动较慢，如窗口已显示可继续等待
  pause & exit /b 1
)
goto waitboot

:bootok
echo [4/4] 安装并启动应用...
"%ADB%" -s emulator-5556 install -r D:\project\kidslock\dist\kidslock-release-universal.apk
"%ADB%" -s emulator-5556 shell appops set com.kidslock.app SYSTEM_ALERT_WINDOW allow
"%ADB%" -s emulator-5556 shell am start -n com.kidslock.app/.MainActivity
echo.
echo 完成！
pause
endlocal
