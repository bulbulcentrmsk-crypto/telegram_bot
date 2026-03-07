# -*- coding: utf-8 -*-
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import qrcode
from io import BytesIO

import config
from database import Session, User, Agent, Request, Center, generate_referral_code
from states import AddAgent, AddRequest, EditCenter, AddCenter
import utils

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
scheduler = AsyncIOScheduler()

# КЛАВИАТУРЫ ----------------------------------------------------------------
def get_start_keyboard(role):
    if role == 'admin':
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton('📊 Статистика'))
        keyboard.add(KeyboardButton('👥 Агенты'))
        keyboard.add(KeyboardButton('📋 Все заявки'))
        keyboard.add(KeyboardButton('🏊 Центры "Буль-Буль"'))
    elif role == 'agent':
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton('🔗 Моя ссылка'))
        keyboard.add(KeyboardButton('📱 QR-код'))
        keyboard.add(KeyboardButton('📊 Мои рефералы'))
        keyboard.add(KeyboardButton('📋 Заявки'))
    else:
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton('📝 Записаться'))
        keyboard.add(KeyboardButton('📞 Контакты'))
        keyboard.add(KeyboardButton('🏊 Наши центры'))
    return keyboard

def get_centers_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton('🏊 Центр на Ленина', callback_data='center_1'),
        InlineKeyboardButton('🏊 Центр на Гагарина', callback_data='center_2'),
        InlineKeyboardButton('🏊 Центр на Пушкина', callback_data='center_3')
    )
    return keyboard

# СТАРТ ---------------------------------------------------------------------
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    
    if not user:
        args = message.get_args()
        invited_by = None
        if args:
            invited_by = session.query(User).filter_by(referral_code=args).first()
        
        role = 'admin' if message.from_user.id in config.ADMIN_IDS else 'referral'
        referral_code = generate_referral_code()
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            role=role,
            referral_code=referral_code,
            invited_by_id=invited_by.id if invited_by else None
        )
        session.add(user)
        session.commit()
        
        if invited_by and invited_by.role == 'agent':
            await bot.send_message(invited_by.telegram_id, 
                f"🎉 У вас новый реферал! Поздравляем! 🎉\n\n{message.from_user.first_name} только что присоединился по вашей ссылке.")
    
    # Приветствие в зависимости от роли
    if user.role == 'admin':
        welcome_text = f"👋 *Привет, {message.from_user.first_name}!*\n\n🔑 Ты вошёл как *администратор* сети «Буль-Буль».\n📊 Управляй агентами и смотри статистику."
    elif user.role == 'agent':
        welcome_text = f"👋 *Привет, {message.from_user.first_name}!*\n\n🤝 Ты вошёл как *агент* сети «Буль-Буль».\n💼 Приглашай родителей и отслеживай записи."
    else:
        welcome_text = f"👋 *Привет, {message.from_user.first_name}!*\n\n🫂 Добро пожаловать в сеть бассейнов *«Буль-Буль»* для самых маленьких!\n\n📝 *Хочешь записаться?* Нажимай «Записаться»\n🏊 *Посмотреть бассейны?* Нажимай «Наши центры»"
    
    await message.answer(welcome_text, reply_markup=get_start_keyboard(user.role), parse_mode='Markdown')
    session.close()

# АГЕНТЫ --------------------------------------------------------------------
@dp.message_handler(lambda message: message.text == '🔗 Моя ссылка')
async def get_referral_link(message: types.Message):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if user and user.role == 'agent':
        bot_username = (await bot.get_me()).username
        await message.answer(f"🔗 Твоя ссылка:\n`https://t.me/{bot_username}?start={user.referral_code}`", parse_mode='Markdown')
    session.close()

@dp.message_handler(lambda message: message.text == '📱 QR-код')
async def generate_qr(message: types.Message):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if user and user.role == 'agent':
        bot_username = (await bot.get_me()).username
        qr = qrcode.make(f"https://t.me/{bot_username}?start={user.referral_code}")
        bio = BytesIO()
        bio.name = 'qr.png'
        qr.save(bio, 'PNG')
        bio.seek(0)
        await message.answer_photo(photo=bio, caption="📱 Твой QR-код")
    session.close()

@dp.message_handler(lambda message: message.text == '📊 Мои рефералы')
async def view_referrals(message: types.Message):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if user and user.role == 'agent':
        referrals = session.query(User).filter_by(invited_by_id=user.id).all()
        if referrals:
            text = "📊 *Твои рефералы:*\n\n"
            for r in referrals:
                text += f"👤 {r.first_name} — {r.registered_at.strftime('%d.%m.%Y')}\n"
        else:
            text = "😢 Пока нет рефералов. Приглашай родителей!"
        await message.answer(text, parse_mode='Markdown')
    session.close()

@dp.message_handler(lambda message: message.text == '📋 Заявки')
async def agent_requests(message: types.Message):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if user and user.role == 'agent':
        agent = session.query(Agent).filter_by(user_id=user.id).first()
        if agent:
            requests = session.query(Request).filter_by(agent_id=agent.id).order_by(Request.created_at.desc()).all()
            if requests:
                text = "📋 *Твои заявки:*\n\n"
                for req in requests[:5]:
                    status_emoji = '⏳' if req.status == 'pending' else '✅' if req.status == 'contacted' else '❌'
                    text += f"{status_emoji} {req.full_name} — {req.created_at.strftime('%d.%m.%Y')}\n"
            else:
                text = "📭 Заявок пока нет."
        else:
            text = "❌ Ты не зарегистрирован как агент."
        await message.answer(text, parse_mode='Markdown')
    session.close()

# ЗАЯВКИ ОТ КЛИЕНТОВ --------------------------------------------------------
@dp.message_handler(lambda message: message.text == '📝 Записаться')
async def start_request(message: types.Message):
    await message.answer("👶 *Как зовут малыша?* (ФИО)", parse_mode='Markdown')
    await AddRequest.waiting_for_full_name.set()

@dp.message_handler(state=AddRequest.waiting_for_full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("📞 *Ваш телефон* (для связи)", parse_mode='Markdown')
    await AddRequest.waiting_for_phone.set()

@dp.message_handler(state=AddRequest.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("📧 *Email* (необязательно)", parse_mode='Markdown')
    await AddRequest.waiting_for_email.set()

@dp.message_handler(state=AddRequest.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer("🏊 *Выбери бассейн:*", reply_markup=get_centers_inline_keyboard(), parse_mode='Markdown')
    await AddRequest.waiting_for_center.set()

@dp.callback_query_handler(lambda c: c.data.startswith('center_'), state=AddRequest.waiting_for_center)
async def process_center(callback: types.CallbackQuery, state: FSMContext):
    center_id = callback.data.split('_')[1]
    await state.update_data(center=center_id)
    await callback.message.answer("💬 *Напиши удобное время или вопрос*", parse_mode='Markdown')
    await AddRequest.waiting_for_message.set()
    await callback.answer()

@dp.message_handler(state=AddRequest.waiting_for_message)
async def process_message(message: types.Message, state: FSMContext):
    session = Session()
    data = await state.get_data()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    
    if user:
        agent = None
        agent_user = None
        if user.invited_by_id:
            agent_user = session.query(User).filter_by(id=user.invited_by_id).first()
            if agent_user:
                agent = session.query(Agent).filter_by(user_id=agent_user.id).first()
        
        req = Request(
            user_id=user.id,
            agent_id=agent.id if agent else None,
            full_name=data['full_name'],
            phone=data['phone'],
            email=data.get('email', ''),
            center=data['center'],
            message=message.text,
            status='pending'
        )
        session.add(req)
        session.commit()
        
        if agent and agent_user and agent_user.telegram_id:
            await bot.send_message(agent_user.telegram_id, 
                f"📝 *Новая заявка!*\n\n👶 {data['full_name']}\n📞 {data['phone']}\n🏊 Центр: {data['center']}\n💬 {message.text}", 
                parse_mode='Markdown')
        
        await message.answer("✅ *Заявка принята!*\n\nМы свяжемся с вами в ближайшее время ☺️", parse_mode='Markdown')
    
    session.close()
    await state.finish()

@dp.message_handler(lambda message: message.text == '📞 Контакты')
async def contacts(message: types.Message):
    text = """
📞 *Контакты «Буль-Буль»*

☎️ *Телефон:* +7 (123) 456-78-90
📧 *Email:* info@bul-bul.ru
🌐 *Сайт:* www.bul-bul.ru

🕒 *Режим работы:* 09:00 — 21:00 (без выходных)

📍 *Главный офис:* ул. Ленина, 10
"""
    await message.answer(text, parse_mode='Markdown')

# ЦЕНТРЫ --------------------------------------------------------------------
@dp.message_handler(lambda message: message.text == '🏊 Центры "Буль-Буль"' or message.text == '🏊 Наши центры')
async def show_centers(message: types.Message):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    centers = session.query(Center).filter_by(is_active=True).all()
    
    if not centers:
        text = "🏊 *Наши бассейны:*\n\n"
        for info in config.CENTERS_INFO.values():
            parts = info.split('\n')
            name = parts[0]
            phone = parts[1].replace('Телефон: ', '📞 ') if len(parts) > 1 else ''
            text += f"💧 *{name}*\n{phone}\n\n"
    else:
        text = "🏊 *Бассейны «Буль-Буль»:*\n\n"
        for c in centers:
            text += f"💧 *{c.name}*\n"
            text += f"📍 {c.address}\n"
            text += f"📞 {c.phone}\n"
            if c.description:
                text += f"📝 {c.description}\n"
            text += "\n"
    
    if user and user.role == 'admin':
        keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton('⚙️ Управление', callback_data='admin_centers'))
        await message.answer(text, parse_mode='Markdown', reply_markup=keyboard)
    else:
        await message.answer(text, parse_mode='Markdown')
    session.close()

# УПРАВЛЕНИЕ ЦЕНТРАМИ (ДЛЯ АДМИНА) -----------------------------------------
@dp.callback_query_handler(lambda c: c.data == 'admin_centers', user_id=config.ADMIN_IDS)
async def admin_centers_menu(callback: types.CallbackQuery):
    session = Session()
    centers = session.query(Center).all()
    text = "🏊 **УПРАВЛЕНИЕ БАССЕЙНАМИ**\n\n"
    if centers:
        for c in centers:
            status = '✅' if c.is_active else '❌'
            text += f"{status} {c.name}\n"
    else:
        text += "Бассейнов нет."
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('➕ Добавить', callback_data='add_center'),
        InlineKeyboardButton('📋 Список', callback_data='list_centers'),
        InlineKeyboardButton('🔄 Из config', callback_data='sync_centers')
    )
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=keyboard)
    await callback.answer()
    session.close()

@dp.callback_query_handler(lambda c: c.data == 'list_centers', user_id=config.ADMIN_IDS)
async def list_centers(callback: types.CallbackQuery):
    session = Session()
    centers = session.query(Center).all()
    if not centers:
        await callback.message.edit_text("📭 Бассейнов нет.")
        await callback.answer()
        session.close()
        return
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    for center in centers:
        status = '✅' if center.is_active else '❌'
        keyboard.add(InlineKeyboardButton(f"{status} {center.name}", callback_data=f'view_center_{center.id}'))
    keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='admin_centers'))
    
    await callback.message.edit_text("🏊 **ВЫБЕРИ БАССЕЙН:**", parse_mode='Markdown', reply_markup=keyboard)
    await callback.answer()
    session.close()

@dp.callback_query_handler(lambda c: c.data.startswith('view_center_'), user_id=config.ADMIN_IDS)
async def view_center(callback: types.CallbackQuery):
    center_id = int(callback.data.split('_')[2])
    session = Session()
    center = session.query(Center).filter_by(id=center_id).first()
    
    if not center:
        await callback.message.edit_text("❌ Бассейн не найден!")
        await callback.answer()
        session.close()
        return
    
    text = f"🏊 **{center.name}**\n📍 {center.address}\n📞 {center.phone}\n📝 {center.description}\n\n{'✅ Активен' if center.is_active else '❌ Неактивен'}"
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('✏️ Название', callback_data=f'edit_name_{center.id}'),
        InlineKeyboardButton('📍 Адрес', callback_data=f'edit_addr_{center.id}'),
        InlineKeyboardButton('📞 Телефон', callback_data=f'edit_phone_{center.id}'),
        InlineKeyboardButton('📝 Описание', callback_data=f'edit_desc_{center.id}'),
        InlineKeyboardButton('🔄 Статус', callback_data=f'toggle_{center.id}'),
        InlineKeyboardButton('❌ Удалить', callback_data=f'del_{center.id}')
    )
    keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='list_centers'))
    
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=keyboard)
    await callback.answer()
    session.close()

# АДМИНКА -------------------------------------------------------------------
@dp.message_handler(lambda message: message.text == '📊 Статистика' and message.from_user.id in config.ADMIN_IDS)
async def admin_stats(message: types.Message):
    session = Session()
    total_users = session.query(User).count()
    total_agents = session.query(User).filter_by(role='agent').count()
    total_referrals = session.query(User).filter_by(role='referral').count()
    total_requests = session.query(Request).count()
    pending_requests = session.query(Request).filter_by(status='pending').count()
    
    text = f"""
📊 *СТАТИСТИКА «БУЛЬ-БУЛЬ»*

👥 *Всего пользователей:* {total_users}
├ 👤 *Агентов:* {total_agents}
└ 👥 *Родителей:* {total_referrals}

📝 *Заявок:* {total_requests}
└ ⏳ *Ожидают:* {pending_requests}

📅 *Дата:* {datetime.now().strftime('%d.%m.%Y')}
"""
    await message.answer(text, parse_mode='Markdown')
    session.close()

@dp.message_handler(lambda message: message.text == '👥 Агенты' and message.from_user.id in config.ADMIN_IDS)
async def admin_agents(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton('➕ Добавить агента', callback_data='add_agent'),
        InlineKeyboardButton('📋 Список агентов', callback_data='list_agents')
    )
    await message.answer("👥 *Управление агентами*", parse_mode='Markdown', reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == '📋 Все заявки' and message.from_user.id in config.ADMIN_IDS)
async def admin_requests(message: types.Message):
    session = Session()
    requests = session.query(Request).order_by(Request.created_at.desc()).all()
    if not requests:
        await message.answer("📭 Заявок нет")
        session.close()
        return
    
    keyboard = InlineKeyboardMarkup(row_width=5)
    buttons = []
    for i, req in enumerate(requests[:10], 1):
        buttons.append(InlineKeyboardButton(str(i), callback_data=f'admin_req_{req.id}'))
    
    for i in range(0, len(buttons), 5):
        keyboard.row(*buttons[i:i+5])
    
    await message.answer(
        f"📋 *Всего заявок:* {len(requests)}\n\nВыберите номер заявки для просмотра:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    session.close()

# ОБРАБОТЧИКИ КОЛЛБЭКОВ ДЛЯ ЗАЯВОК -----------------------------------------
@dp.callback_query_handler(lambda c: c.data.startswith('admin_req_'), user_id=config.ADMIN_IDS)
async def view_admin_request(callback: types.CallbackQuery):
    req_id = int(callback.data.split('_')[2])
    session = Session()
    req = session.query(Request).filter_by(id=req_id).first()
    
    if not req:
        await callback.answer("❌ Заявка не найдена")
        session.close()
        return
    
    status_emoji = {'pending': '⏳', 'contacted': '✅', 'closed': '❌'}.get(req.status, '⏳')
    status_text = {'pending': 'Ожидает', 'contacted': 'Связались', 'closed': 'Закрыта'}.get(req.status, 'Ожидает')
    
    agent_name = "Не назначен"
    if req.agent_id:
        agent = session.query(Agent).filter_by(id=req.agent_id).first()
        if agent:
            agent_name = agent.full_name
    
    text = f"📋 *Заявка #{req.id}*\n"
    text += f"{status_emoji} *Статус:* {status_text}\n\n"
    text += f"👶 *Ребёнок:* {req.full_name}\n"
    text += f"📞 *Телефон:* {req.phone}\n"
    text += f"📧 *Email:* {req.email or '—'}\n"
    text += f"🏊 *Центр:* {req.center}\n"
    text += f"👤 *Агент:* {agent_name}\n\n"
    text += f"💬 *Сообщение:*\n{req.message}\n\n"
    text += f"📅 *Создана:* {req.created_at.strftime('%d.%m.%Y %H:%M')}"
    
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton('⏳ Ожидает', callback_data=f'admin_status_{req.id}_pending'),
        InlineKeyboardButton('✅ Связались', callback_data=f'admin_status_{req.id}_contacted'),
        InlineKeyboardButton('❌ Закрыть', callback_data=f'admin_status_{req.id}_closed')
    )
    keyboard.add(InlineKeyboardButton('🔙 Назад к списку', callback_data='admin_back_to_requests'))
    
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=keyboard)
    await callback.answer()
    session.close()

@dp.callback_query_handler(lambda c: c.data.startswith('admin_status_'), user_id=config.ADMIN_IDS)
async def change_admin_status(callback: types.CallbackQuery):
    parts = callback.data.split('_')
    req_id = int(parts[2])
    new_status = parts[3]
    
    session = Session()
    req = session.query(Request).filter_by(id=req_id).first()
    if req:
        req.status = new_status
        session.commit()
        await callback.answer(f"Статус изменён")
        
        new_callback = types.CallbackQuery(
            id=callback.id,
            from_user=callback.from_user,
            message=callback.message,
            chat_instance=callback.chat_instance,
            data=f'admin_req_{req_id}'
        )
        await view_admin_request(new_callback)
    session.close()

@dp.callback_query_handler(lambda c: c.data == 'admin_back_to_requests', user_id=config.ADMIN_IDS)
async def back_to_admin_requests(callback: types.CallbackQuery):
    await admin_requests(callback.message)
    await callback.answer()

# ДОБАВЛЕНИЕ АГЕНТА ---------------------------------------------------------
@dp.callback_query_handler(lambda c: c.data == 'add_agent', user_id=config.ADMIN_IDS)
async def add_agent_start(callback: types.CallbackQuery):
    await callback.message.answer("👤 *Введите ФИО агента:*", parse_mode='Markdown')
    await AddAgent.waiting_for_full_name.set()
    await callback.answer()

@dp.message_handler(state=AddAgent.waiting_for_full_name, user_id=config.ADMIN_IDS)
async def add_agent_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("📞 *Введите телефон агента:*", parse_mode='Markdown')
    await AddAgent.waiting_for_phone.set()

@dp.message_handler(state=AddAgent.waiting_for_phone, user_id=config.ADMIN_IDS)
async def add_agent_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("📧 *Введите email агента:*", parse_mode='Markdown')
    await AddAgent.waiting_for_email.set()

@dp.message_handler(state=AddAgent.waiting_for_email, user_id=config.ADMIN_IDS)
async def add_agent_email(message: types.Message, state: FSMContext):
    session = Session()
    data = await state.get_data()
    
    referral_code = generate_referral_code()
    user = User(
        telegram_id=None,
        username=None,
        first_name=data['full_name'].split()[0],
        last_name=' '.join(data['full_name'].split()[1:]),
        role='agent',
        referral_code=referral_code
    )
    session.add(user)
    session.flush()
    
    agent = Agent(
        user_id=user.id,
        full_name=data['full_name'],
        phone=data['phone'],
        email=message.text
    )
    session.add(agent)
    session.commit()
    
    bot_username = (await bot.get_me()).username
    success_text = f"""
✅ *Агент добавлен!*

👤 *ФИО:* {data['full_name']}
📞 *Телефон:* {data['phone']}
📧 *Email:* {message.text}

🔗 *Ссылка для входа:*
`https://t.me/{bot_username}?start={referral_code}`

📱 Отправьте эту ссылку агенту
"""
    await message.answer(success_text, parse_mode='Markdown')
    
    session.close()
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'list_agents', user_id=config.ADMIN_IDS)
async def list_agents(callback: types.CallbackQuery):
    session = Session()
    agents = session.query(Agent).all()
    if agents:
        text = "📋 *Список агентов:*\n\n"
        for agent in agents:
            user = session.query(User).filter_by(id=agent.user_id).first()
            status = '✅' if user and user.telegram_id else '❌'
            text += f"{status} *{agent.full_name}*\n📞 {agent.phone}\n\n"
    else:
        text = "📭 Агентов пока нет"
    await callback.message.answer(text, parse_mode='Markdown')
    await callback.answer()
    session.close()

# РЕДАКТИРОВАНИЕ ЦЕНТРОВ ----------------------------------------------------
@dp.callback_query_handler(lambda c: c.data.startswith('edit_name_'), user_id=config.ADMIN_IDS)
async def edit_name_start(callback: types.CallbackQuery, state: FSMContext):
    center_id = int(callback.data.split('_')[2])
    await state.update_data(center_id=center_id)
    await callback.message.answer("✏️ *Введите новое название бассейна:*", parse_mode='Markdown')
    await EditCenter.waiting_for_name.set()
    await callback.answer()

@dp.message_handler(state=EditCenter.waiting_for_name, user_id=config.ADMIN_IDS)
async def save_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    session = Session()
    center = session.query(Center).filter_by(id=data['center_id']).first()
    if center:
        center.name = message.text
        session.commit()
        await message.answer(f"✅ Название изменено на: {message.text}")
    session.close()
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('edit_addr_'), user_id=config.ADMIN_IDS)
async def edit_addr_start(callback: types.CallbackQuery, state: FSMContext):
    center_id = int(callback.data.split('_')[2])
    await state.update_data(center_id=center_id)
    await callback.message.answer("📍 *Введите новый адрес:*", parse_mode='Markdown')
    await EditCenter.waiting_for_address.set()
    await callback.answer()

@dp.message_handler(state=EditCenter.waiting_for_address, user_id=config.ADMIN_IDS)
async def save_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    session = Session()
    center = session.query(Center).filter_by(id=data['center_id']).first()
    if center:
        center.address = message.text
        session.commit()
        await message.answer(f"✅ Адрес изменён на: {message.text}")
    session.close()
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('edit_phone_'), user_id=config.ADMIN_IDS)
async def edit_phone_start(callback: types.CallbackQuery, state: FSMContext):
    center_id = int(callback.data.split('_')[2])
    await state.update_data(center_id=center_id)
    await callback.message.answer("📞 *Введите новый телефон:*", parse_mode='Markdown')
    await EditCenter.waiting_for_phone.set()
    await callback.answer()

@dp.message_handler(state=EditCenter.waiting_for_phone, user_id=config.ADMIN_IDS)
async def save_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    session = Session()
    center = session.query(Center).filter_by(id=data['center_id']).first()
    if center:
        center.phone = message.text
        session.commit()
        await message.answer(f"✅ Телефон изменён на: {message.text}")
    session.close()
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('edit_desc_'), user_id=config.ADMIN_IDS)
async def edit_desc_start(callback: types.CallbackQuery, state: FSMContext):
    center_id = int(callback.data.split('_')[2])
    await state.update_data(center_id=center_id)
    await callback.message.answer("📝 *Введите новое описание:*", parse_mode='Markdown')
    await EditCenter.waiting_for_description.set()
    await callback.answer()

@dp.message_handler(state=EditCenter.waiting_for_description, user_id=config.ADMIN_IDS)
async def save_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    session = Session()
    center = session.query(Center).filter_by(id=data['center_id']).first()
    if center:
        center.description = message.text
        session.commit()
        await message.answer("✅ Описание обновлено")
    session.close()
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('toggle_'), user_id=config.ADMIN_IDS)
async def toggle_center(callback: types.CallbackQuery):
    center_id = int(callback.data.split('_')[1])
    session = Session()
    center = session.query(Center).filter_by(id=center_id).first()
    if center:
        center.is_active = not center.is_active
        session.commit()
        await callback.answer(f"Статус изменён")
    session.close()

@dp.callback_query_handler(lambda c: c.data.startswith('del_'), user_id=config.ADMIN_IDS)
async def delete_center_confirm(callback: types.CallbackQuery):
    center_id = int(callback.data.split('_')[1])
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton('✅ Да', callback_data=f'confirm_del_{center_id}'),
        InlineKeyboardButton('❌ Нет', callback_data=f'view_center_{center_id}')
    )
    await callback.message.edit_text("⚠️ *Удалить бассейн?*", parse_mode='Markdown', reply_markup=keyboard)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('confirm_del_'), user_id=config.ADMIN_IDS)
async def delete_center(callback: types.CallbackQuery):
    center_id = int(callback.data.split('_')[2])
    session = Session()
    center = session.query(Center).filter_by(id=center_id).first()
    if center:
        name = center.name
        session.delete(center)
        session.commit()
        await callback.message.edit_text(f"✅ Бассейн '{name}' удалён")
    session.close()
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'add_center', user_id=config.ADMIN_IDS)
async def add_center_start(callback: types.CallbackQuery):
    await callback.message.answer("🏊 *Введите название нового бассейна:*", parse_mode='Markdown')
    await AddCenter.waiting_for_name.set()
    await callback.answer()

@dp.message_handler(state=AddCenter.waiting_for_name, user_id=config.ADMIN_IDS)
async def add_center_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📍 *Введите адрес:*", parse_mode='Markdown')
    await AddCenter.waiting_for_address.set()

@dp.message_handler(state=AddCenter.waiting_for_address, user_id=config.ADMIN_IDS)
async def add_center_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("📞 *Введите телефон:*", parse_mode='Markdown')
    await AddCenter.waiting_for_phone.set()

@dp.message_handler(state=AddCenter.waiting_for_phone, user_id=config.ADMIN_IDS)
async def add_center_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("📝 *Введите описание:*", parse_mode='Markdown')
    await AddCenter.waiting_for_description.set()

@dp.message_handler(state=AddCenter.waiting_for_description, user_id=config.ADMIN_IDS)
async def add_center_description(message: types.Message, state: FSMContext):
    session = Session()
    data = await state.get_data()
    center = Center(
        name=data['name'],
        address=data['address'],
        phone=data['phone'],
        description=message.text,
        is_active=True
    )
    session.add(center)
    session.commit()
    await message.answer(f"✅ Бассейн '{data['name']}' добавлен!")
    session.close()
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'sync_centers', user_id=config.ADMIN_IDS)
async def sync_centers(callback: types.CallbackQuery):
    session = Session()
    session.query(Center).delete()
    for cid, info in config.CENTERS_INFO.items():
        parts = info.split('\n')
        name = parts[0].split(' - ')[0]
        address = parts[0].split(' - ')[1] if ' - ' in parts[0] else ''
        phone = parts[1].replace('Телефон: ', '') if len(parts) > 1 else ''
        center = Center(
            name=name,
            address=address,
            phone=phone,
            description=info,
            is_active=True
        )
        session.add(center)
    session.commit()
    await callback.message.edit_text("✅ Бассейны синхронизированы")
    await callback.answer()
    session.close()

# НАПОМИНАНИЯ ---------------------------------------------------------------
async def send_reminders():
    session = Session()
    one_day_ago = datetime.now() - timedelta(days=1)
    pending = session.query(Request).filter(
        Request.status == 'pending',
        Request.created_at <= one_day_ago,
        Request.reminder_count < 3
    ).all()
    
    for req in pending:
        user = session.query(User).filter_by(id=req.user_id).first()
        if user and user.telegram_id:
            try:
                await bot.send_message(
                    user.telegram_id, 
                    f"⏰ *Напоминание*\n\nВы оставляли заявку в «Буль-Буль». Мы всё ещё ждём вас! Напишите, если есть вопросы.",
                    parse_mode='Markdown'
                )
                req.reminder_count += 1
                session.commit()
            except:
                pass
    session.close()

# ЗАПУСК --------------------------------------------------------------------
# ============= УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК =============
@dp.message_handler()
async def debug_all_messages(message: types.Message):
    print(f"🔥 Сообщение: '{message.text}' от {message.from_user.id}")
    
    # Проверяем, админ ли пользователь
    is_admin = message.from_user.id in config.ADMIN_IDS
    print(f"🔥 Админ: {is_admin}")
    
    # Просто отвечаем на любое сообщение
    await message.answer(f"Тест: получено '{message.text}'. Админ: {is_admin}")
    
if __name__ == '__main__':
    scheduler.add_job(send_reminders, 'interval', hours=24)
    scheduler.start()
    executor.start_polling(dp, skip_updates=True)
