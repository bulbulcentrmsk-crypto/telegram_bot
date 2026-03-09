# -*- coding: utf-8 -*-
import os
import glob
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

CREDENTIALS_FILE = 'drive-credentials.json'
EXPORTS_FOLDER = 'exports'
DRIVE_FOLDER_ID = '1ZUAHwD4w58U8aTwkUfBLOAM_R_plWJeb'  

def get_drive_service():
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=credentials, cache_discovery=False)

def upload_all_csv():
    if not os.path.exists(EXPORTS_FOLDER):
        print("❌ Папка exports не найдена")
        return

    csv_files = glob.glob(os.path.join(EXPORTS_FOLDER, "*.csv"))
    if not csv_files:
        print("📭 Нет CSV файлов")
        return

    service = get_drive_service()
    print(f"📁 Загружаем {len(csv_files)} файлов в папку {DRIVE_FOLDER_ID}")

    for file_path in csv_files:
        file_name = os.path.basename(file_path)
        media = MediaFileUpload(file_path, mimetype='text/csv', resumable=True)
        file_metadata = {'name': file_name, 'parents': [DRIVE_FOLDER_ID]}
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        print(f"✅ {file_name} → {file.get('webViewLink')}")

if __name__ == "__main__":
    upload_all_csv()