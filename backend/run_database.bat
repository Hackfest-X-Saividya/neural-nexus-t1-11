@echo off
title Neural Crime - Forensic Database API Server
echo ========================================================
echo   Starting Neural Crime Forensic Database API Server...
echo ========================================================
echo.

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py app.py
    goto end
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python app.py
    goto end
)

if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" (
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" app.py
    goto end
)

echo [ERROR] Python not found in PATH. Please install Python from python.org.
pause

:end
