# -*- coding: utf-8 -*-
from aiogram.dispatcher.filters.state import State, StatesGroup

class AddAgent(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_phone = State()
    waiting_for_place_of_work = State()  # место работы (был email)

class AddRequest(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_birth_date = State()     # дата рождения
    waiting_for_phone = State()
    waiting_for_center = State()
    waiting_for_message = State()

class EditCenter(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()
    waiting_for_phone = State()
    waiting_for_description = State()

class AddCenter(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()
    waiting_for_phone = State()
    waiting_for_description = State()
