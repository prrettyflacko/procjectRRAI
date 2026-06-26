# Образ бэкенда DataMind (FastAPI + LangGraph).
# Зависимости ставим через uv по локфайлу — воспроизводимо.
FROM python:3.12-slim

# uv — быстрый менеджер пакетов.
RUN pip install --no-cache-dir uv

WORKDIR /app

# Сначала только манифесты — чтобы слой с зависимостями кэшировался.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Затем код приложения.
COPY app ./app

EXPOSE 8000

# Запуск API. Слушаем 0.0.0.0, чтобы был доступен снаружи контейнера.
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
