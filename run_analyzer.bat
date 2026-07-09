@echo off
setlocal

if "%~1"=="" (
    echo Usage: run_analyzer.bat path\to\file.apk
    exit /b 1
)

set "APK_FILE=%~f1"
if not exist "%APK_FILE%" (
    echo APK file not found: %APK_FILE%
    exit /b 1
)

for %%I in ("%APK_FILE%") do (
    set "APK_DIR=%%~dpI"
    set "APK_NAME=%%~nxI"
)
if "%APK_DIR:~-1%"=="\" set "APK_DIR=%APK_DIR:~0,-1%"

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "DATA_DIR=%SCRIPT_DIR%\data"

if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

docker build -t apk-analyzer "%SCRIPT_DIR%"
if errorlevel 1 exit /b 1

docker run --rm ^
  -v "%DATA_DIR%:/app/data" ^
  -v "%APK_DIR%:/app/input:ro" ^
  apk-analyzer "/app/input/%APK_NAME%"
