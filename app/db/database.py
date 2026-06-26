"""Подключение к базе данных.

Здесь создаётся engine (соединение с PostgreSQL), фабрика сессий и базовый класс
для моделей. Зависимость get_db() отдаёт сессию в эндпоинты FastAPI и закрывает её
после запроса.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

# engine — точка подключения к БД. URL берём из .env (DATABASE_URL).
engine = create_engine(settings.DATABASE_URL)

# Фабрика сессий: каждая сессия — это «разговор» с БД в рамках одного запроса.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Базовый класс, от которого наследуются все модели таблиц.
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Зависимость FastAPI: открывает сессию на время запроса и закрывает после."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
