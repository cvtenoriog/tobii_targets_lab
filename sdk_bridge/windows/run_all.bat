@echo off
REM --- Ajusta el path de tu MinGW ---
set PATH=C:\mingw\bin;%PATH%

REM --- Compilar gaze.cpp ---
echo Compilando gaze.cpp...
g++ src\gaze.cpp -o build\gaze.exe -Iinclude -Llib/x86 -ltobii_stream_engine
if ERRORLEVEL 1 (
    echo Error compilando gaze.cpp
    pause
    exit /b 1
)

REM --- Compilar gaze_server.cpp ---
echo Compilando gaze_server.cpp...
g++ src\gaze_server.cpp -o build\gaze_server.exe -Iinclude -Llib/x86 -ltobii_stream_engine -lws2_32
if ERRORLEVEL 1 (
    echo Error compilando gaze_server.cpp
    pause
    exit /b 1
)

REM --- Ejecutar gaze.exe ---
echo Lanzando gaze.exe...
start "" build\gaze.exe

REM --- Ejecutar gaze_server.exe ---
echo Lanzando gaze_server.exe...
start "" build\gaze_server.exe

REM --- Ejecutar targets.py ---
echo Lanzando game.py...
python game\game.py

REM --- Al cerrar targets.py, cerrar gaze.exe y gaze_server.exe ---
echo Cerrando procesos...
taskkill /IM gaze.exe /F >nul 2>&1
taskkill /IM gaze_server.exe /F >nul 2>&1

pause
