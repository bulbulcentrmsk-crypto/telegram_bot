@echo off
chcp 65001 >nul
echo Запуск экспорта и загрузки на Google Drive...
call venv\Scripts\activate
python export_all.py
python auto_upload_to_drive.py
pause