"""Точка входа FastAPI-приложения DataMind."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import datasets, query
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

app.include_router(datasets.router)
app.include_router(query.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
