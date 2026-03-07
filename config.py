import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS_STR = os.getenv('ADMIN_IDS', '')

if ADMIN_IDS_STR:
    ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(',') if id.strip()]
else:
    # Твой ID, если переменная не загрузилась
    ADMIN_IDS = [217070285]

if not BOT_TOKEN:
    raise ValueError("Токен бота не найден в файле .env!")
else:
    print(f"Токен загружен: {BOT_TOKEN[:10]}...")

# Тексты для авто-напоминаний
DEFAULT_REMINDER_TEXTS = {
    'first_reminder': '👋 Здравствуйте! Вы оставляли заявку в центре «Буль-Буль». Есть ли у вас вопросы?',
    'second_reminder': '⏰ Напоминаем о вашей заявке в «Буль-Буль». Мы готовы ответить на все вопросы!',
    'third_reminder': '💙 Если у вас изменились планы, пожалуйста, сообщите нам в «Буль-Буль».'
}

# Информация о центрах «Буль-Буль» в Челябинске
CENTERS_INFO = {
    '1': {
        'name': 'Центр на 40-летия Победы',
        'address': 'Челябинск, ул. 40-летия Победы, 45Б',
        'phone': '+7 (922) 750-16-03',
        'description': '🧜‍♂️ Сеть центров раннего плавания от 1 месяца до 10 лет'
    },
    '2': {
        'name': 'Центр на Комсомольском',
        'address': 'Челябинск, пр. Комсомольский, 37в',
        'phone': '+7 (922) 750-16-03',
        'description': '🧜‍♂️ Сеть центров раннего плавания от 1 месяца до 2 лет'
    },
    '3': {
        'name': 'Центр на Воровского',
        'address': 'Челябинск, ул. Воровского, 63а',
        'phone': '+7 (922) 750-16-03',
        'description': '🧜‍♂️ Сеть центров раннего плавания от 1 месяца до 2 лет'
    },
    '4': {
        'name': 'Центр на Братьев Кашириных',
        'address': 'ул. Братьев Кашириных, 87а',
        'phone': '+7 (922) 750-16-03',
        'description': '🧜‍♂️ Сеть центров раннего плавания от 1 месяца до 2 лет'
    }
}

# Для обратной совместимости с кодом, где используется старый формат
CENTERS_INFO_SIMPLE = {
    '1': f"🏊 {CENTERS_INFO['1']['name']}\n📍 {CENTERS_INFO['1']['address']}\n📞 {CENTERS_INFO['1']['phone']}\n{CENTERS_INFO['1']['description']}",
    '2': f"🏊 {CENTERS_INFO['2']['name']}\n📍 {CENTERS_INFO['2']['address']}\n📞 {CENTERS_INFO['2']['phone']}\n{CENTERS_INFO['2']['description']}",
    '3': f"🏊 {CENTERS_INFO['3']['name']}\n📍 {CENTERS_INFO['3']['address']}\n📞 {CENTERS_INFO['3']['phone']}\n{CENTERS_INFO['3']['description']}",
    '4': f"🏊 {CENTERS_INFO['4']['name']}\n📍 {CENTERS_INFO['4']['address']}\n📞 {CENTERS_INFO['4']['phone']}\n{CENTERS_INFO['4']['description']}"
}
