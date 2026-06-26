"""Модели таблиц (SQLAlchemy).

Три таблицы по схеме из задания:
- datasets      — один загруженный CSV-файл (метаданные).
- dataset_rows  — строки этого CSV; каждая строка хранится как JSON в колонке row_data.
- query_log     — история вопросов пользователя и ответов системы.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    # Ключ (путь) исходного файла в Selectel S3. None, если S3 не настроен.
    s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Связь: у датасета много строк. cascade — удалим строки вместе с датасетом.
    rows: Mapped[list["DatasetRow"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class DatasetRow(Base):
    __tablename__ = "dataset_rows"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), index=True)
    row_index: Mapped[int] = mapped_column(Integer)
    # Вся строка CSV как словарь {колонка: значение}.
    row_data: Mapped[dict] = mapped_column(JSONB)

    dataset: Mapped["Dataset"] = relationship(back_populates="rows")


class QueryLog(Base):
    __tablename__ = "query_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
