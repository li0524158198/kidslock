@echo off
setlocal enabledelayedexpansion
rem KidsLock JVM logic regression: compiles the REAL Android production sources
rem (PrefManager/QuestionBank) against the Android shims and runs them on a
rem desktop JVM. No Android device or SDK required.
rem
rem Usage:
rem   qa\jvm\run.bat          run JvmTests (main regression: bank engine + state machine)
rem   qa\jvm\run.bat csv      run CsvMatrix (cross-platform CSV matrix; M4 needs a
rem                           harmony-side export first, otherwise it is SKIPped)

set "JVMDIR=%~dp0"
if "%JVMDIR:~-1%"=="\" set "JVMDIR=%JVMDIR:~0,-1%"
for %%I in ("%JVMDIR%\..\..") do set "ROOT=%%~fI"

where javac >nul 2>nul
if errorlevel 1 (
    echo [ERROR] javac not found in PATH. JDK 8+ is required.
    exit /b 1
)

set "OUT=%JVMDIR%\out"
set "CP=%JVMDIR%\vendor\org.json.jar"
set "ARGFILE=%JVMDIR%\out\sources.txt"
if not exist "%OUT%" mkdir "%OUT%"
if exist "%ARGFILE%" del "%ARGFILE%"

rem Enumerate sources into a javac @argfile (JDK8 javac does not glob quoted paths;
rem backslashes are escape chars inside argfiles, so write forward-slash paths)
for /r "%JVMDIR%\shims" %%F in (*.java) do (
    set "p=%%F"
    echo "!p:\=/!">>"%ARGFILE%"
)
set "p=%ROOT%\kidslock-src\app\src\main\java\com\kidslock\app\PrefManager.java"
echo "!p:\=/!">>"%ARGFILE%"
set "p=%ROOT%\kidslock-src\app\src\main\java\com\kidslock\app\QuestionBank.java"
echo "!p:\=/!">>"%ARGFILE%"
for %%F in ("%JVMDIR%\src\*.java") do (
    set "p=%%F"
    echo "!p:\=/!">>"%ARGFILE%"
)

javac -encoding UTF-8 -d "%OUT%" -cp "%CP%" @"%ARGFILE%"
if errorlevel 1 (
    echo [ERROR] Compilation failed.
    exit /b 1
)

set "MAIN=JvmTests"
if /i "%~1"=="csv" set "MAIN=CsvMatrix"

java -cp "%OUT%;%CP%" "-Dkidslock.root=%ROOT%" "-Dkidslock.filedir=%JVMDIR%\filedir" %MAIN%
exit /b %errorlevel%
