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
            await bot.send_message(invited_by.telegram_id, f"🎉 Новый реферал: {message.from_user.first_name}")
    else:
        if message.from_user.id in config.ADMIN_IDS and user.role != 'admin':
            user.role = 'admin'
            session.commit()
    
    role_text = {'admin': 'администратор', 'agent': 'агент', 'referral': 'клиент'}.get(user.role, 'клиент')
    await message.answer(f"👋 Здравствуйте, {message.from_user.first_name}! Вы вошли как {role_text}.", reply_markup=get_start_keyboard(user.role))
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
            text = "📊 Твои рефералы:\n\n"
            for r in referrals:
                text += f"• {r.first_name} - {r.registered_at.strftime('%d.%m.%Y')}\n"
        else:
            text = "Пока нет рефералов."
        await message.answer(text)
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
                text = "📋 Твои заявки:\n\n"
                for req in requests[:5]:
                    text += f"• {req.full_name} - {req.status}\n"
            else:
                text = "Заявок нет."
        else:
            text = "Ты не агент."
        await message.answer(text)
    session.close()

# ЗАЯВКИ ОТ КЛИЕНТОВ --------------------------------------------------------
@dp.message_handler(lambda message: message.text == '📝 Заявка')
async def start_request(message: types.Message):
    await message.answer("Введите ФИО:")
    await AddRequest.waiting_for_full_name.set()

@dp.message_handler(state=AddRequest.waiting_for_full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Телефон:")
    await AddRequest.waiting_for_phone.set()

@dp.message_handler(state=AddRequest.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("Email (необязательно):")
    await AddRequest.waiting_for_email.set()

@dp.message_handler(state=AddRequest.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer("Выбери центр:", reply_markup=get_centers_inline_keyboard())
    await AddRequest.waiting_for_center.set()

@dp.callback_query_handler(lambda c: c.data.startswith('center_'), state=AddRequest.waiting_for_center)
async def process_center(callback: types.CallbackQuery, state: FSMContext):
    center_id = callback.data.split('_')[1]
    await state.update_data(center=center_id)
    await callback.message.answer("Опишите вопрос:")
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
            await bot.send_message(agent_user.telegram_id, f"📝 Новая заявка от {data['full_name']}")
        
        await message.answer("✅ Заявка принята!")
    
    session.close()
    await state.finish()

@dp.message_handler(lambda message: message.text == '📞 Контакты')
async def contacts(message: types.Message):
    await message.answer("📞 +7 (123) 456-78-90\n📧 info@medical.ru")

# ЦЕНТРЫ --------------------------------------------------------------------
@dp.message_handler(lambda message: message.text == '🏥 Центры')
async def show_centers(message: types.Message):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    centers = session.query(Center).filter_by(is_active=True).all()
    
    if not centers:
        text = "🏥 Центры:\n\n" + "\n\n".join([info for info in config.CENTERS_INFO.values()])
    else:
        text = "🏥 Центры:\n\n"
        for c in centers:
            text += f"**{c.name}**\n📍 {c.address}\n📞 {c.phone}\n{c.description}\n\n"
    
    if user and user.role == 'admin':
        keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton('⚙️ Управление', callback_data='admin_centers'))
        await message.answer(text, parse_mode='Markdown', reply_markup=keyboard)
    else:
        await message.answer(text, parse_mode='Markdown')
    session.close()

@dp.callback_query_handler(lambda c: c.data == 'admin_centers', user_id=config.ADMIN_IDS)
async def admin_centers_menu(callback: types.CallbackQuery):
    session = Session()
    centers = session.query(Center).all()
    text = "🏥 **УПРАВЛЕНИЕ ЦЕНТРАМИ**\n\n"
    if centers:
        for c in centers:
            status = '✅' if c.is_active else '❌'
            text += f"{status} {c.name}\n"
    else:
        text += "Центров нет."
    
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
        await callback.message.edit_text("📭 Центров нет.")
        await callback.answer()
        session.close()
        return
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    for center in centers:
        status = '✅' if center.is_active else '❌'
        keyboard.add(InlineKeyboardButton(f"{status} {center.name}", callback_data=f'view_center_{center.id}'))
    keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='admin_centers'))
    
    await callback.message.edit_text("📋 **ВЫБЕРИ ЦЕНТР:**", parse_mode='Markdown', reply_markup=keyboard)
    await callback.answer()
    session.close()

@dp.callback_query_handler(lambda c: c.data.startswith('view_center_'), user_id=config.ADMIN_IDS)
async def view_center(callback: types.CallbackQuery):
    center_id = int(callback.data.split('_')[2])
    session = Session()
    center = session.query(Center).filter_by(id=center_id).first()
    
    if not center:
        await callback.message.edit_text("❌ Центр не найден!")
        await callback.answer()
        session.close()
        return
    
    text = f"🏥 **{center.name}**\n📍 {center.address}\n📞 {center.phone}\n📝 {center.description}\n\n{'✅ Активен' if center.is_active else '❌ Неактивен'}"
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
    
    text = f"📊 **СТАТИСТИКА**\n\n"
    text += f"👥 Всего пользователей: {total_users}\n"
    text += f"👤 Агентов: {total_agents}\n"
    text += f"👥 Рефералов: {total_referrals}\n"
    text += f"📝 Заявок: {total_requests}"
    
    await message.answer(text, parse_mode='Markdown')
    session.close()

@dp.message_handler(lambda message: message.text == '👥 Агенты' and message.from_user.id in config.ADMIN_IDS)
async def admin_agents(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton('➕ Добавить', callback_data='add_agent'),
        InlineKeyboardButton('📋 Список', callback_data='list_agents')
    )
    await message.answer("👥 Управление агентами:", reply_markup=keyboard)

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
        buttons.append(InlineKeyboardButton(str(i), callback_data=f'req_{req.id}'))
    for i in range(0, len(buttons), 5):
        keyboard.row(*buttons[i:i+5])
    
    await message.answer(f"📋 Заявок: {len(requests)}. Выбери номер:", reply_markup=keyboard)
    session.close()

@dp.callback_query_handler(lambda c: c.data.startswith('req_'), user_id=config.ADMIN_IDS)
async def view_request(callback: types.CallbackQuery):
    req_id = int(callback.data.split('_')[1])
    session = Session()
    req = session.query(Request).filter_by(id=req_id).first()
    
    if not req:
        await callback.answer("❌ Не найдена")
        session.close()
        return
    
    status_emoji = {'pending': '⏳', 'contacted': '✅', 'closed': '❌'}.get(req.status, '⏳')
    text = f"📋 **Заявка #{req.id}**\n{status_emoji} {req.status}\n\n"
    text += f"👤 {req.full_name}\n📞 {req.phone}\n📧 {req.email}\n🏥 {req.center}\n\n"
    text += f"📝 {req.message}"
    
    keyboard = InlineKeyboardMarkup(row_width=3).add(
        InlineKeyboardButton('⏳ Ожидает', callback_data=f'status_{req.id}_pending'),
        InlineKeyboardButton('✅ Связались', callback_data=f'status_{req.id}_contacted'),
        InlineKeyboardButton('❌ Закрыть', callback_data=f'status_{req.id}_closed')
    )
    keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_requests'))
    
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=keyboard)
    await callback.answer()
    session.close()

@dp.callback_query_handler(lambda c: c.data.startswith('status_'), user_id=config.ADMIN_IDS)
async def change_status(callback: types.CallbackQuery):
    parts = callback.data.split('_')
    req_id = int(parts[1])
    new_status = parts[2]
    
    session = Session()
    req = session.query(Request).filter_by(id=req_id).first()
    if req:
        req.status = new_status
        session.commit()
        await callback.answer(f"Статус изменен")
        
        # Обновляем отображение
        new_callback = types.CallbackQuery(
            id=callback.id,
            from_user=callback.from_user,
            message=callback.message,
            chat_instance=callback.chat_instance,
            data=f'req_{req_id}'
        )
        await view_request(new_callback)
    session.close()

@dp.callback_query_handler(lambda c: c.data == 'back_to_requests', user_id=config.ADMIN_IDS)
async def back_to_requests(callback: types.CallbackQuery):
    await admin_requests(callback.message)
    await callback.answer()

# ДОБАВЛЕНИЕ АГЕНТА ---------------------------------------------------------
@dp.callback_query_handler(lambda c: c.data == 'add_agent', user_id=config.ADMIN_IDS)
async def add_agent_start(callback: types.CallbackQuery):
    await callback.message.answer("Введите ФИО агента:")
    await AddAgent.waiting_for_full_name.set()
    await callback.answer()

@dp.message_handler(state=AddAgent.waiting_for_full_name, user_id=config.ADMIN_IDS)
async def add_agent_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Телефон:")
    await AddAgent.waiting_for_phone.set()

@dp.message_handler(state=AddAgent.waiting_for_phone, user_id=config.ADMIN_IDS)
async def add_agent_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("Email:")
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
    await message.answer(f"✅ Агент добавлен!\nСсылка: https://t.me/{bot_username}?start={referral_code}")
    
    session.close()
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'list_agents', user_id=config.ADMIN_IDS)
async def list_agents(callback: types.CallbackQuery):
    session = Session()
    agents = session.query(Agent).all()
    if agents:
        text = "📋 **Агенты:**\n\n"
        for agent in agents:
            user = session.query(User).filter_by(id=agent.user_id).first()
            status = '✅' if user and user.telegram_id else '❌'
            text += f"{status} {agent.full_name} - {agent.phone}\n"
    else:
        text = "Агентов нет"
    await callback.message.answer(text, parse_mode='Markdown')
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
            texts = ['первое', 'второе', 'третье']
            try:
                await bot.send_message(user.telegram_id, f"⏰ {texts[req.reminder_count]} напоминание")
                req.reminder_count += 1
                session.commit()
            except:
                pass
    session.close()

# ЗАПУСК --------------------------------------------------------------------
if __name__ == '__main__':
    scheduler.add_job(send_reminders, 'interval', hours=24)
    scheduler.start()
    executor.start_polling(dp, skip_updates=True)
