@echo off
REM View today's logs from project directory
REM Usage: logs          — show today's log
REM        logs tail     — follow live (like tail -f)
REM        logs dir      — open log folder

set LOGDIR=%USERPROFILE%\.mortgage-rag\logs
set LOGFILE=%LOGDIR%\rag_%date:~-4%%date:~4,2%%date:~7,2%.log

if "%1"=="dir" (
    explorer "%LOGDIR%"
    exit /b
)

if "%1"=="tail" (
    powershell -Command "Get-Content '%LOGFILE%' -Wait"
    exit /b
)

if exist "%LOGFILE%" (
    powershell -Command "Get-Content '%LOGFILE%'"
) else (
    echo No log file found for today: %LOGFILE%
)
