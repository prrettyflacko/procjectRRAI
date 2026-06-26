"""Точка входа FastAPI-приложения DataMind."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

# Чтобы наши логи (например, проверка файла в S3) были видны в выводе сервера.
logging.basicConfig(level=logging.INFO)

from app.api import datasets, query
from app.auth import require_api_key
from app.db.database import Base, engine
from app.db import models  # noqa: F401 — нужен, чтобы модели зарегистрировались в Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # На старте создаём таблицы, если их ещё нет (без Alembic — для учебного проекта).
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="DataMind",
    description="Мультиагентная система анализа данных на базе LangGraph + FastAPI + SQL + Selectel",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(datasets.router, dependencies=[Depends(require_api_key)])
app.include_router(query.router, dependencies=[Depends(require_api_key)])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
