@echo off
chcp 65001 >nul
title Stand Manager — Compilacion

cd /d "%~dp0"

echo.
echo  Compilando Stand Manager...
echo  -----------------------------------------------

pyinstaller lebl_parking.spec --clean -y
if errorlevel 1 (
    echo.
    echo  ERROR: fallo la compilacion.
    pause
    exit /b 1
)

echo.
echo  Limpiando archivos temporales...
if exist build rmdir /s /q build
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d"
)

echo  Limpiando cache de PyInstaller...
if exist "%LOCALAPPDATA%\pyinstaller" rmdir /s /q "%LOCALAPPDATA%\pyinstaller"
if exist "%TEMP%\_MEI*" del /f /q "%TEMP%\_MEI*" 2>nul
for /d %%d in ("%TEMP%\_MEI*") do rmdir /s /q "%%d" 2>nul

echo.
echo  Refrescando cache de iconos de Windows...
ie4uinit.exe -show 2>nul || ie4uinit.exe -ClearIconCache 2>nul

echo.
echo  Listo. EXE generado en: dist\LEBL Parking.exe
echo.
pause
