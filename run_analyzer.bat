@echo off
REM Запуск APK Analyzer через Docker.
REM
REM Usage:
REM   run_analyzer.bat path\to\app.apk                              REM статика
REM   run_analyzer.bat path\to\app.apk --mode dynamic --package com.example
REM   run_analyzer.bat path\to\app.apk --mode full --package com.example

setlocal enabledelayedexpansion

if "%~1"=="" (
    echo Usage: run_analyzer.bat path\to\file.apk [--mode static^|dynamic^|full] [--package pkg] [--emulator-host host]
    exit /b 1
)

set "APK_FILE=%~f1"
set "APK_DIR=%~dp1"
set "APK_NAME=%~nx1"
if "%APK_DIR:~-1%"=="\" set "APK_DIR=%APK_DIR:~0,-1%"

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "DATA_DIR=%SCRIPT_DIR%\data"

if not exist "%APK_FILE%" (
    echo APK file not found: %APK_FILE%
    exit /b 1
)

if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

REM Сдвигаем %1, собираем остальные аргументы
shift
set "EXTRA_ARGS="
set "MODE=static"
:parse
if "%~1"=="" goto parsed
if /i "%~1"=="--mode" (
    set "MODE=%~2"
)
set "EXTRA_ARGS=%EXTRA_ARGS% %~1"
shift
goto parse
:parsed

REM Выбор Dockerfile по режиму
if /i "%MODE%"=="static" (
    set "IMAGE_TAG=apk-analyzer-static"
    set "DOCKERFILE=Dockerfile.static"
) else if /i "%MODE%"=="dynamic" (
    set "IMAGE_TAG=apk-analyzer-dynamic"
    set "DOCKERFILE=Dockerfile.dynamic"
) else if /i "%MODE%"=="full" (
    set "IMAGE_TAG=apk-analyzer-dynamic"
    set "DOCKERFILE=Dockerfile.dynamic"
) else (
    echo Unknown mode: %MODE%
    exit /b 1
)

echo Building image: %IMAGE_TAG% ^(Dockerfile: %DOCKERFILE%^)
docker build -t %IMAGE_TAG% -f "%SCRIPT_DIR%\%DOCKERFILE%" "%SCRIPT_DIR%"
if errorlevel 1 exit /b 1

if "%EMULATOR_HOST%"=="" set "EMULATOR_HOST=android-emulator"

docker run --rm ^
  -v "%DATA_DIR%:/app/data" ^
  -v "%APK_DIR%:/app/input:ro" ^
  -e EMULATOR_HOST=%EMULATOR_HOST% ^
  %IMAGE_TAG% "/app/input/%APK_NAME%" %EXTRA_ARGS%

endlocal
