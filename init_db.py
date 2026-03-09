# -*- coding: utf-8 -*-
from database import Base, engine

if __name__ == '__main__':
    print("🚀 Создаём таблицы в базе данных...")
    Base.metadata.create_all(engine)
    print("✅ База данных успешно создана!")