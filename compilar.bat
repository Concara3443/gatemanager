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

echo.
echo  Listo. EXE generado en: dist\LEBL Parking.exe
echo.
pause
