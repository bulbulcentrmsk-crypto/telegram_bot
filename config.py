# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS_STR = os.getenv('ADMIN_IDS', '')

# Преобразуем ADMIN_IDS в список чисел
if ADMIN_IDS_STR:
    ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(',') if id.strip()]
else:
    ADMIN_IDS = []

# Проверка, что токен загружен
if not BOT_TOKEN:
    raise ValueError("Токен бота не найден в файле .env!")
else:
    print(f"Токен загружен: {BOT_TOKEN[:10]}...")

# Тексты для авто-напоминаний
DEFAULT_REMINDER_TEXTS = {
    'first_reminder': 'Здравствуйте! Вы оставляли заявку. Есть ли у вас вопросы?',
    'second_reminder': 'Напоминаем о нашей заявке. Мы готовы ответить на все вопросы!',
    'third_reminder': 'Если у вас изменились планы, пожалуйста, сообщите нам.'
}

# Информация о центрах
CENTERS_INFO = {
    '1': 'Медицинский центр "Здоровье" - ул. Ленина, 10\nТелефон: +7 (123) 456-78-90',
    '2': 'Диагностический центр "Профи" - ул. Гагарина, 25\nТелефон: +7 (123) 456-78-91',
    '3': 'Центр реабилитации "Восстановление" - ул. Пушкина, 5\nТелефон: +7 (123) 456-78-92'
}