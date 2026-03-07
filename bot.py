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
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    if role == 'admin':
        keyboard.add(KeyboardButton('📊 Статистика'))
        keyboard.add(KeyboardButton('👥 Агенты'))
        keyboard.add(KeyboardButton('📋 Все заявки'))
        keyboard.add(KeyboardButton('🏥 Центры'))
    elif role == 'agent':
        keyboard.add(KeyboardButton('🔗 Моя ссылка'))
        keyboard.add(KeyboardButton('📱 QR-код'))
        keyboard.add(KeyboardButton('📊 Мои рефералы'))
        keyboard.add(KeyboardButton('📋 Заявки'))
    else:
        keyboard.add(KeyboardButton('📝 Заявка'))
        keyboard.add(KeyboardButton('🏥 Центры'))
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
    
    # Приветствие
    if user.role == 'admin':
        welcome_text = f"👋 Здравствуйте, {message.from_user.first_name}! Вы вошли как **администратор**."
    elif user.role == 'agent':
        welcome_text = f"👋 Здравствуйте, {message.from_user.first_name}! Вы вошли как **агент**."
    else:
        welcome_text = f"👋 Здравствуйте, {message.from_user.first_name}! Добро пожаловать!"
    
    await message.answer(welcome_text, reply_markup=get_start_keyboard(user.role), parse_mode='Markdown')
    session.close()

# ============= АДМИНКА =============
@dp.message_handler(lambda message: message.text == '📊 Статистика')
async def stats_handler(message: types.Message):
    session = Session()
    text = f"📊 **СТАТИСТИКА**\n\n"
    text += f"👥 Всего пользователей: {session.query(User).count()}\n"
    text += f"👤 Агентов: {session.query(User).filter_by(role='agent').count()}\n"
    text += f"👥 Рефералов: {session.query(User).filter_by(role='referral').count()}\n"
    text += f"📝 Заявок: {session.query(Request).count()}"
    await message.answer(text, parse_mode='Markdown')
    session.close()

@dp.message_handler(lambda message: message.text == '👥 Агенты')
async def agents_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton('➕ Добавить', callback_data='add_agent'),
        InlineKeyboardButton('📋 Список', callback_data='list_agents')
    )
    await message.answer("👥 Управление агентами:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == '📋 Все заявки')
async def all_requests_handler(message: types.Message):
    session = Session()
    requests = session.query(Request).order_by(Request.created_at.desc()).all()
    if not requests:
        await message.answer("📭 Заявок нет")
        session.close()
        return
    
    text = "📋 **Последние заявки:**\n\n"
    for req in requests[:5]:
        status = {'pending': '⏳', 'contacted': '✅', 'closed': '❌'}.get(req.status, '⏳')
        text += f"{status} {req.full_name} - {req.created_at.strftime('%d.%m.%Y')}\n"
    
    await message.answer(text, parse_mode='Markdown')
    session.close()

# ============= АГЕНТЫ =============
@dp.message_handler(lambda message: message.text == '🔗 Моя ссылка')
async def link_handler(message: types.Message):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if user:
        bot_username = (await bot.get_me()).username
        await message.answer(f"🔗 Твоя ссылка:\n`https://t.me/{bot_username}?start={user.referral_code}`", parse_mode='Markdown')
    session.close()

@dp.message_handler(lambda message: message.text == '📱 QR-код')
async def qr_handler(message: types.Message):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if user:
        bot_username = (await bot.get_me()).username
        qr = qrcode.make(f"https://t.me/{bot_username}?start={user.referral_code}")
        bio = BytesIO()
        bio.name = 'qr.png'
        qr.save(bio, 'PNG')
        bio.seek(0)
        await message.answer_photo(photo=bio, caption="📱 Твой QR-код")
    session.close()

@dp.message_handler(lambda message: message.text == '📊 Мои рефералы')
async def my_refs_handler(message: types.Message):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if user:
        referrals = session.query(User).filter_by(invited_by_id=user.id).all()
        if referrals:
            text = "📊 Твои рефералы:\n\n" + "\n".join([f"• {r.first_name}" for r in referrals])
        else:
            text = "Пока нет рефералов."
        await message.answer(text)
    session.close()

@dp.message_handler(lambda message: message.text == '📋 Заявки')
async def my_requests_handler(message: types.Message):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if user and user.role == 'agent':
        agent = session.query(Agent).filter_by(user_id=user.id).first()
        if agent:
            requests = session.query(Request).filter_by(agent_id=agent.id).all()
            if requests:
                text = "📋 Твои заявки:\n\n" + "\n".join([f"• {r.full_name}" for r in requests[:5]])
            else:
                text = "Заявок нет."
        else:
            text = "Ты не агент."
        await message.answer(text)
    session.close()

# ============= КЛИЕНТЫ =============
@dp.message_handler(lambda message: message.text == '📝 Заявка')
async def new_request_handler(message: types.Message):
    await message.answer("Введите ваше ФИО:")
    await AddRequest.waiting_for_full_name.set()

@dp.message_handler(lambda message: message.text == '📞 Контакты')
async def contacts_handler(message: types.Message):
    await message.answer("📞 +7 (123) 456-78-90\n📧 info@medical.ru")

# ============= ЦЕНТРЫ =============
@dp.message_handler(lambda message: message.text == '🏥 Центры')
async def centers_handler(message: types.Message):
    session = Session()
    centers = session.query(Center).filter_by(is_active=True).all()
    
    if not centers:
        text = "🏥 Центры:\n\n" + "\n\n".join([info for info in config.CENTERS_INFO.values()])
    else:
        text = "🏥 Центры:\n\n" + "\n\n".join([f"**{c.name}**\n{c.address}\n{c.phone}" for c in centers])
    
    await message.answer(text, parse_mode='Markdown')
    session.close()

# ============= CALLBACKS =============
@dp.callback_query_handler(lambda c: c.data == 'add_agent')
async def add_agent_start(callback: types.CallbackQuery):
    await callback.message.answer("Введите ФИО агента:")
    await AddAgent.waiting_for_full_name.set()
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'list_agents')
async def list_agents(callback: types.CallbackQuery):
    session = Session()
    agents = session.query(Agent).all()
    if agents:
        text = "📋 **Агенты:**\n\n" + "\n".join([f"• {a.full_name} - {a.phone}" for a in agents])
    else:
        text = "Агентов нет"
    await callback.message.answer(text, parse_mode='Markdown')
    await callback.answer()
    session.close()

# ============= СОСТОЯНИЯ =============
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
    await message.answer("Кратко опишите вопрос:")
    await AddRequest.waiting_for_message.set()

@dp.message_handler(state=AddRequest.waiting_for_message)
async def process_message(message: types.Message, state: FSMContext):
    session = Session()
    data = await state.get_data()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    
    if user:
        req = Request(
            user_id=user.id,
            full_name=data['full_name'],
            phone=data['phone'],
            email=data.get('email', ''),
            center='Не указан',
            message=message.text,
            status='pending'
        )
        session.add(req)
        session.commit()
        await message.answer("✅ Заявка принята!")
    
    session.close()
    await state.finish()

@dp.message_handler(state=AddAgent.waiting_for_full_name)
async def add_agent_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Телефон:")
    await AddAgent.waiting_for_phone.set()

@dp.message_handler(state=AddAgent.waiting_for_phone)
async def add_agent_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("Email:")
    await AddAgent.waiting_for_email.set()

@dp.message_handler(state=AddAgent.waiting_for_email)
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

# НАПОМИНАНИЯ ---------------------------------------------------------------
async def send_reminders():
    session = Session()
    one_day_ago = datetime.now() - timedelta(days=1)
    pending = session.query(Request).filter(Request.status=='pending', Request.created_at<=one_day_ago, Request.reminder_count<3).all()
    for req in pending:
        user = session.query(User).filter_by(id=req.user_id).first()
        if user and user.telegram_id:
            texts = ['первое', 'второе', 'третье']
            try:
                await bot.send_message(user.telegram_id, f"⏰ {texts[req.reminder_count]} напоминание")
                req.reminder_count += 1
                session.commit()
            except: pass
    session.close()

# ЗАПУСК --------------------------------------------------------------------
if __name__ == '__main__':
    scheduler.add_job(send_reminders, 'interval', hours=24)
    scheduler.start()
    executor.start_polling(dp, skip_updates=True)
