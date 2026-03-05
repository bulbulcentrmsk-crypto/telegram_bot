@echo off
chcp 65001 >nul
echo Запуск экспорта данных...
call venv\Scripts\activate
python export_all.py
pause