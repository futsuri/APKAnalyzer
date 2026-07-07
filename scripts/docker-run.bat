@echo off
setlocal

if "%~1"=="" (
    echo Usage: scripts\docker-run.bat path\to\app.apk [extra analyzer args]
    exit /b 1
)

set "APK_PATH=%~f1"
set "APK_DIR=%~dp1"
set "APK_FILE=%~nx1"
shift

docker run --rm ^
    -v "%CD%\data:/app/data" ^
    -v "%APK_DIR%:/input:ro" ^
    apk-analyzer "/input/%APK_FILE%" %*

exit /b %ERRORLEVEL%
