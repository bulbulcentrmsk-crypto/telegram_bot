# -*- coding: utf-8 -*-
import re
from datetime import datetime

def validate_phone(phone):
    """Проверка формата телефона"""
    pattern = re.compile(r'^\+?[0-9]{10,15}$')
    return pattern.match(phone) is not None

def validate_email(email):
    """Проверка формата email"""
    pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return pattern.match(email) is not None

def format_date(date):
    """Форматирование даты"""
    return date.strftime('%d.%m.%Y %H:%M') if date else 'Не указано'

def get_agent_statistics(session, agent_id):
    """Получение статистики агента"""
    from database import User, Request
    
    # Количество рефералов
    referrals_count = session.query(User).filter_by(invited_by_id=agent_id).count()
    
    # Количество заявок от рефералов
    requests_count = session.query(Request).filter_by(agent_id=agent_id).count()
    
    # Количество обработанных заявок
    processed_requests = session.query(Request).filter_by(
        agent_id=agent_id, 
        status='contacted'
    ).count()
    
    return {
        'referrals': referrals_count,
        'total_requests': requests_count,
        'processed_requests': processed_requests
    }