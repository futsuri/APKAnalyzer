@echo off
setlocal enabledelayedexpansion

if "%~1"=="" (
    echo Usage: run_analyzer.bat ^<path_to_apk^> [additional_arguments]
    echo Example: run_analyzer.bat app.apk --debug
    exit /b 1
)

set "APK_PATH=%~f1"
if not exist "!APK_PATH!" (
    echo Error: APK file does not exist at !APK_PATH!
    exit /b 1
)

echo ==========================================================
echo [1/2] Building Docker image 'apk-analyzer'...
echo ==========================================================
docker build -t apk-analyzer "%~dp0"

if errorlevel 1 (
    echo Error: Failed to build Docker image.
    exit /b 1
)

rem Shift first argument (the APK path)
shift
set "ARGS="
:loop
if not "%~1"=="" (
    set "ARGS=!ARGS! %1"
    shift
    goto loop
)

echo.
echo ==========================================================
echo [2/2] Running analysis on !APK_PATH!...
echo ==========================================================
docker run --rm -it -v "%cd%\data:/app/data" -v "!APK_PATH!:/app/input.apk" apk-analyzer /app/input.apk !ARGS!
