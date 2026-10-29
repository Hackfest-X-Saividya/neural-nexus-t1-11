@echo off
title Neural Crime - Forensic Database Viewer
echo ========================================================
echo   Loading Neural Crime Forensic Database Records...
echo ========================================================
echo.

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py view_database.py
    goto end
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python view_database.py
    goto end
)

if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" (
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" view_database.py
    goto end
)

echo [ERROR] Python not found in PATH.
pause

:end
echo.
pause
