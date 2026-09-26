@echo off
rem Messger dev server - WebSocket uchun daphne kerak (runserver emas!)
rem Ikkalasi bitta portda ishlay olmaydi: avval eski serverni yoping.

cd /d "%~dp0"

echo Avval eski server to'xtatiladi (agar ishlayotgan bo'lsa)...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%p >nul 2>&1
)

echo Chiquvchi: python -m daphne -b 127.0.0.1 -p 8000 config.asgi:application
python -m daphne -b 127.0.0.1 -p 8000 config.asgi:application

pause