"""Эндпоинты Части 1: загрузка CSV и просмотр данных.

- POST /upload                     — загрузить CSV, распарсить и сохранить строки в БД.
- GET  /datasets                   — список загруженных датасетов.
- GET  /datasets/{id}/rows         — постраничный просмотр строк датасета.
"""

import csv
import io

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Dataset, DatasetRow
from app.schemas import DatasetOut, RowOut, UploadResult
from app.storage import s3

router = APIRouter(tags=["datasets"])


@router.post("/upload", response_model=UploadResult)
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResult:
    """Принимает CSV-файл, парсит его, сохраняет строки в БД и кладёт файл в S3."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Ожидается файл с расширением .csv")

    content = await file.read()
    try:
        # utf-8-sig убирает BOM, если он есть (частый случай у CSV из Excel).
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Файл должен быть в кодировке UTF-8")

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV пустой или без строк данных")

    # 1) Создаём запись о датасете и получаем его id (flush без commit).
    dataset = Dataset(name=file.filename, row_count=len(rows))
    db.add(dataset)
    db.flush()

    # 2) Заливаем исходный файл в S3 (если ключи Selectel настроены).
    if s3.is_configured():
        s3_key = f"datasets/{dataset.id}/{file.filename}"
        s3.upload_bytes(content, s3_key)
        dataset.s3_key = s3_key
        # Фоновая проверка: файл действительно появился в S3 (head_object).
        background_tasks.add_task(s3.verify_uploaded, s3_key)

    # 3) Сохраняем каждую строку CSV как JSON.
    db.add_all(
        DatasetRow(dataset_id=dataset.id, row_index=i, row_data=row)
        for i, row in enumerate(rows)
    )
    db.commit()
    db.refresh(dataset)

    return UploadResult(
        dataset_id=dataset.id, name=dataset.name, row_count=dataset.row_count
    )


@router.get("/datasets", response_model=list[DatasetOut])
def list_datasets(db: Session = Depends(get_db)) -> list[Dataset]:
    """Возвращает список всех загруженных датасетов."""
    return list(db.scalars(select(Dataset).order_by(Dataset.created_at.desc())))


@router.get("/datasets/{dataset_id}/rows", response_model=list[RowOut])
def get_rows(
    dataset_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[DatasetRow]:
    """Постраничный просмотр строк датасета."""
    if db.get(Dataset, dataset_id) is None:
        raise HTTPException(status_code=404, detail="Датасет не найден")

    stmt = (
        select(DatasetRow)
        .where(DatasetRow.dataset_id == dataset_id)
        .order_by(DatasetRow.row_index)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))


@router.get("/datasets/{dataset_id}/download")
def download_dataset(dataset_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    """Возвращает presigned URL (15 минут) на скачивание исходного файла из S3."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Датасет не найден")
    if not dataset.s3_key:
        raise HTTPException(
            status_code=404, detail="Для этого датасета нет файла в S3"
        )
    return {"url": s3.presigned_url(dataset.s3_key)}
