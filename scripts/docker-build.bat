@echo off
setlocal

docker build -t apk-analyzer .
exit /b %ERRORLEVEL%
