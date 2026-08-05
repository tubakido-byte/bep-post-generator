@echo off
chcp 65001 > nul
cd /d C:\Users\htate\pr_meeting\bep-post-generator-repo

set PYTHONIOENCODING=utf-8
set PYTHON_EXE=C:\Users\htate\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe
set LOG_DIR=C:\Users\htate\pr_meeting\bep-post-generator-repo\pr_post_logs
set TODAY=%DATE:/=-%

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set LOG_FILE=%LOG_DIR%\autopost_%TODAY%.log

echo [%DATE% %TIME%] AutoPost START >> "%LOG_FILE%"
%PYTHON_EXE% post_kdp_from_csv.py --next-round-robin --execute >> "%LOG_FILE%" 2>&1
echo [%DATE% %TIME%] AutoPost END (exit=%ERRORLEVEL%) >> "%LOG_FILE%"

exit /b %ERRORLEVEL%
