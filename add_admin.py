# -*- coding: utf-8 -*-
from database import Session, User, generate_referral_code
from datetime import datetime

# ВАШИ ДАННЫЕ - ПРОВЕРЬТЕ ИХ!
YOUR_TELEGRAM_ID = 217070285  # Ваш ID из @userinfobot
YOUR_FIRST_NAME = "Админ"
YOUR_USERNAME = "admin"

session = Session()

user = session.query(User).filter_by(telegram_id=YOUR_TELEGRAM_ID).first()

if user:
    user.role = 'admin'
    print(f"✅ Пользователь {user.first_name} обновлен до администратора")
else:
    new_admin = User(
        telegram_id=YOUR_TELEGRAM_ID,
        username=YOUR_USERNAME,
        first_name=YOUR_FIRST_NAME,
        last_name="",
        role='admin',
        referral_code=generate_referral_code(),
        registered_at=datetime.now(),
        is_active=True
    )
    session.add(new_admin)
    print(f"✅ Создан новый администратор {YOUR_FIRST_NAME}")

session.commit()
session.close()
print("✅ Готово! Теперь вы администратор.")