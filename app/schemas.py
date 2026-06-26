"""Pydantic-схемы запросов и ответов API.

Они описывают, как выглядят данные на входе и выходе эндпоинтов, и заодно
автоматически документируются в Swagger (/docs).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ---- Датасеты ----

class DatasetOut(BaseModel):
    id: int
    name: str
    row_count: int
    created_at: datetime

    # Разрешаем создавать схему прямо из объекта SQLAlchemy.
    model_config = ConfigDict(from_attributes=True)


class UploadResult(BaseModel):
    dataset_id: int
    name: str
    row_count: int


class RowOut(BaseModel):
    row_index: int
    row_data: dict


# ---- Запросы к агенту ----

class QueryRequest(BaseModel):
    dataset_id: int
    question: str
    session_id: str


class QueryResponse(BaseModel):
    answer: str
    needs_clarification: bool
    sql: str | None = None
