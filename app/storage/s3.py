"""Клиент Selectel Object Storage (S3-совместимый).

Selectel работает через стандартный boto3 — как AWS S3, только с другим endpoint_url.
Здесь собраны три операции, нужные проекту: загрузка файла, presigned-ссылка на скачивание
и проверка наличия файла (head_object).
"""

import logging

import boto3

from app.config import settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    """True, если ключи Selectel заданы в .env (иначе работу с S3 пропускаем)."""
    return bool(settings.SELECTEL_ACCESS_KEY and settings.SELECTEL_SECRET_KEY)


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.SELECTEL_ENDPOINT,
        aws_access_key_id=settings.SELECTEL_ACCESS_KEY,
        aws_secret_access_key=settings.SELECTEL_SECRET_KEY,
        region_name=settings.SELECTEL_REGION,
    )


def upload_bytes(data: bytes, key: str) -> None:
    """Заливает байты файла в бакет под ключом key."""
    _client().put_object(Bucket=settings.SELECTEL_BUCKET, Key=key, Body=data)


def presigned_url(key: str, expires: int = 900) -> str:
    """Генерирует временную ссылку на скачивание (по умолчанию 15 минут = 900 сек)."""
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.SELECTEL_BUCKET, "Key": key},
        ExpiresIn=expires,
    )


def delete_object(key: str) -> None:
    """Удаляет файл из бакета (при удалении датасета)."""
    try:
        _client().delete_object(Bucket=settings.SELECTEL_BUCKET, Key=key)
        logger.info("S3: файл %s удалён", key)
    except Exception as exc:  # noqa: BLE001
        logger.error("S3: не удалось удалить %s: %s", key, exc)


def verify_uploaded(key: str) -> None:
    """Фоновая проверка: действительно ли файл появился в S3. Результат пишем в лог."""
    try:
        _client().head_object(Bucket=settings.SELECTEL_BUCKET, Key=key)
        logger.info("S3: файл %s успешно загружен и доступен", key)
    except Exception as exc:  # noqa: BLE001
        logger.error("S3: файл %s НЕ найден после загрузки: %s", key, exc)
