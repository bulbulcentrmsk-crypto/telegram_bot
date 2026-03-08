from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import random
import string

Base = declarative_base()
engine = create_engine('sqlite:///bot_database.db')
Session = sessionmaker(bind=engine)

def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    role = Column(String, default='referral')
    referral_code = Column(String, unique=True)
    invited_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    registered_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)
    
    invited_by = relationship('User', remote_side=[id], backref='referrals')

class Agent(Base):
    __tablename__ = 'agents'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    full_name = Column(String)
    phone = Column(String)
    email = Column(String, nullable=True)  # больше не спрашиваем, оставлено для совместимости
    place_of_work = Column(String, nullable=True)  # новое поле
    created_at = Column(DateTime, default=datetime.now)

class Request(Base):
    __tablename__ = 'requests'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=True)
    full_name = Column(String)
    birth_date = Column(String, nullable=True)  # новое поле
    phone = Column(String)
    email = Column(String, nullable=True)  # больше не используем
    center = Column(String)
    message = Column(Text)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=datetime.now)
    last_reminder_sent = Column(DateTime, nullable=True)
    reminder_count = Column(Integer, default=0)

class ReminderTemplate(Base):
    __tablename__ = 'reminder_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    text = Column(Text)
    days_delay = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)

class Center(Base):
    __tablename__ = 'centers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    address = Column(String)
    phone = Column(String)
    description = Column(Text)
    is_active = Column(Boolean, default=True)

# Create tables
if __name__ == '__main__':
    Base.metadata.create_all(engine)
    print("База данных создана успешно!")