"""Конфигурация приложения.

Все настройки читаются из файла .env (см. .env.example).
pydantic-settings сам подхватывает переменные окружения и приводит их к нужным типам.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # База данных
    DATABASE_URL: str

    # Защита API: если задан — каждый запрос должен слать заголовок X-API-Key.
    # Пусто (по умолчанию) — защита выключена (удобно для локальной разработки).
    API_KEY: str = ""

    # LLM (polza.ai — OpenAI-совместимый шлюз)
    POLZA_API_KEY: str
    POLZA_BASE_URL: str = "https://api.polza.ai/api/v1"
    LLM_MODEL: str = "deepseek/deepseek-v4-flash"

    # Selectel Object Storage (S3) — понадобится на Этапе 3
    SELECTEL_ENDPOINT: str = "https://s3.selectel.ru"
    SELECTEL_ACCESS_KEY: str = ""
    SELECTEL_SECRET_KEY: str = ""
    SELECTEL_BUCKET: str = "datamind-files"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Один общий экземпляр настроек на всё приложение.
settings = Settings()
