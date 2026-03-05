# -*- coding: utf-8 -*-
import csv
import os
from database import Session, Agent, User, Request
from datetime import datetime

print("=" * 50)
print("ЭКСПОРТ ДАННЫХ В CSV")
print("=" * 50)

# Создаем папку для экспортов
if not os.path.exists('exports'):
    os.makedirs('exports')
    print("✅ Папка 'exports' создана")
else:
    print("✅ Папка 'exports' уже существует")

session = Session()
date_str = datetime.now().strftime('%Y%m%d_%H%M%S')

# ============= ЭКСПОРТ АГЕНТОВ =============
print("\n👥 Экспорт агентов...")
agents = session.query(Agent).all()
print(f"   Найдено агентов: {len(agents)}")

if agents:
    filename = f'exports/agents_{date_str}.csv'
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'ФИО', 'Телефон', 'Email', 'Статус', 'Рефералов', 'Заявок'])
        
        for agent in agents:
            user = session.query(User).filter_by(id=agent.user_id).first()
            if user:
                referrals = session.query(User).filter_by(invited_by_id=user.id).count()
                requests = session.query(Request).filter_by(agent_id=agent.id).count()
                status = '✅ Зарегистрирован' if user.telegram_id else '❌ Не зарегистрирован'
            else:
                referrals = 0
                requests = 0
                status = '❌ Нет аккаунта'
            
            writer.writerow([agent.id, agent.full_name, agent.phone, agent.email, status, referrals, requests])
    
    print(f"   ✅ Файл создан: {filename}")
else:
    print("   ⚠️ Агентов нет для экспорта")

# ============= ЭКСПОРТ КЛИЕНТОВ =============
print("\n👥 Экспорт клиентов...")
clients = session.query(User).filter_by(role='referral').all()
print(f"   Найдено клиентов: {len(clients)}")

if clients:
    filename = f'exports/clients_{date_str}.csv'
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Имя', 'Telegram ID', 'Дата', 'Пригласил агент'])
        
        for client in clients:
            agent_name = 'Прямая регистрация'
            if client.invited_by_id:
                inviter = session.query(User).filter_by(id=client.invited_by_id).first()
                if inviter:
                    agent = session.query(Agent).filter_by(user_id=inviter.id).first()
                    agent_name = agent.full_name if agent else 'Агент (без профиля)'
            
            writer.writerow([
                client.id,
                f"{client.first_name} {client.last_name or ''}".strip(),
                client.telegram_id or '—',
                client.registered_at.strftime('%d.%m.%Y'),
                agent_name
            ])
    
    print(f"   ✅ Файл создан: {filename}")
else:
    print("   ⚠️ Клиентов нет для экспорта")

# ============= ЭКСПОРТ ЗАЯВОК =============
print("\n📝 Экспорт заявок...")
requests = session.query(Request).order_by(Request.created_at.desc()).all()
print(f"   Найдено заявок: {len(requests)}")

if requests:
    filename = f'exports/requests_{date_str}.csv'
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Дата', 'Клиент', 'Телефон', 'Центр', 'Статус'])
        
        for req in requests[:100]:  # Последние 100 заявок
            writer.writerow([
                req.id,
                req.created_at.strftime('%d.%m.%Y %H:%M'),
                req.full_name,
                req.phone,
                req.center,
                req.status
            ])
    
    print(f"   ✅ Файл создан: {filename}")
else:
    print("   ⚠️ Заявок нет для экспорта")

session.close()

print("\n" + "=" * 50)
print("✅ ЭКСПОРТ ЗАВЕРШЕН")
print("=" * 50)