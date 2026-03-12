@echo off
chcp 65001 >nul
title LEBL Parking Assignment GUI

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python no encontrado.
    start ms-windows-store://search/?query=Python
    pause
    exit /b 1
)

python "%~dp0parking_gui.py"
if %errorlevel% neq 0 pause
