from database import Base, engine
Base.metadata.create_all(engine)
print("✅ База данных успешно создана! Колонка birth_date добавлена.")