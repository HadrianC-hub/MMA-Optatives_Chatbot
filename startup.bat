@echo off
setlocal

:: Leer token desde token.txt
set /p TOKEN=<token.txt

:: Ejecutar el script Python con el token como argumento
py main.py %TOKEN%

pause
