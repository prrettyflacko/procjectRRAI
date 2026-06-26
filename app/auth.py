"""Простейшая защита API по ключу.

Клиент (наш Streamlit UI) обязан слать заголовок X-API-Key. Сервер сверяет его с
настройкой API_KEY из .env. Так публично открытый API не сможет дёргать кто угодно.

Если API_KEY пустой — защита выключена (удобно при локальной разработке).
"""

from fastapi import Header, HTTPException

from app.config import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not settings.API_KEY:
        return  # защита не настроена — пропускаем
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Неверный или отсутствующий API-ключ")
