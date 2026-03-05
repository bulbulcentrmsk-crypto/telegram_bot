# -*- coding: utf-8 -*-
from database import Session, User
import os
from dotenv import load_dotenv

load_dotenv()
admin_ids_str = os.getenv('ADMIN_IDS', '')
print(f"ADMIN_IDS из .env: {admin_ids_str}")

session = Session()
users = session.query(User).all()
print(f"\nВсего пользователей в базе: {len(users)}")

for user in users:
    print(f"\n--- Пользователь ---")
    print(f"Telegram ID: {user.telegram_id}")
    print(f"Имя: {user.first_name}")
    print(f"Роль: {user.role}")

session.close()