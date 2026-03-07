# -*- coding: utf-8 -*-
import subprocess

print("🚀 ПОЛНЫЙ ЭКСПОРТ + ЗАГРУЗКА")
print("=" * 40)

print("\n📊 Экспорт в CSV...")
subprocess.run(['python', 'export_all.py'])

print("\n☁️ Загрузка на Google Drive...")
subprocess.run(['python', 'auto_upload_to_drive.py'])

print("\n✅ Готово!")