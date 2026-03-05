from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_start_keyboard(role):
    if role == 'admin':
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton('📊 Статистика'))
        keyboard.add(KeyboardButton('👥 Агенты'))
        keyboard.add(KeyboardButton('⚙️ Настройки'))
        keyboard.add(KeyboardButton('📝 Шаблоны напоминаний'))
        keyboard.add(KeyboardButton('🏥 Центры'))
    elif role == 'agent':
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton('🔗 Моя реферальная ссылка'))
        keyboard.add(KeyboardButton('📱 QR-код'))
        keyboard.add(KeyboardButton('📊 Мои рефералы'))
        keyboard.add(KeyboardButton('📋 Заявки'))
    else:  # referral
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton('📝 Оставить заявку'))
        keyboard.add(KeyboardButton('🏥 Наши центры'))
        keyboard.add(KeyboardButton('📞 Контакты'))
    
    return keyboard

def get_centers_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton('Медицинский центр "Здоровье"', callback_data='center_1'),
        InlineKeyboardButton('Диагностический центр "Профи"', callback_data='center_2'),
        InlineKeyboardButton('Центр реабилитации "Восстановление"', callback_data='center_3')
    )
    return keyboard

def get_admin_agents_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('➕ Добавить агента', callback_data='add_agent'),
        InlineKeyboardButton('📊 Статистика агентов', callback_data='agents_stats')
    )
    return keyboard