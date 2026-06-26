# 🤖 DataMind

Мультиагентная система анализа данных на базе **LangGraph + FastAPI + SQL + Selectel S3**.

Пользователь загружает CSV-файлы или задаёт вопросы на естественном языке, а система
разбирает запрос через цепочку LangGraph-агентов, обращается к базе данных и возвращает
структурированный ответ.

Полное описание задания — в [phase3_README.md](phase3_README.md).

## Структура проекта

```
project/
├── app/
│   ├── api/          # FastAPI роутеры
│   ├── agents/       # LangGraph граф и узлы
│   ├── db/           # SQLAlchemy модели и миграции
│   ├── storage/      # Клиент Selectel S3
│   └── main.py
├── data/             # Тестовый датасет orders.csv
├── .env.example
├── docker-compose.yml
└── README.md
```

## Стек

| Технология | Роль |
|---|---|
| LangGraph | Граф агентов: роутинг, инструменты, синтез ответа |
| FastAPI | REST API: загрузка файлов, запросы, история сессий |
| PostgreSQL | Хранение данных, истории запросов, логов агентов |
| Selectel Object Storage | Хранение исходных CSV (S3-совместимый API) |

## API эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| POST | `/upload` | Загрузить CSV: парсинг → строки в БД (+ файл в S3, если настроен) |
| GET | `/datasets` | Список загруженных датасетов |
| GET | `/datasets/{id}/rows?limit=&offset=` | Постраничный просмотр строк |
| GET | `/datasets/{id}/download` | Presigned URL (15 мин) на скачивание из S3 |
| POST | `/query` | Вопрос на естественном языке → ответ через граф LangGraph |
| GET | `/health` | Проверка живости сервиса |

### Граф агентов (`POST /query`)

```
router ──(ясно)──→ sql_agent ──→ synthesizer ──→ ответ
   │
   └──(неясно)──→ clarifier ──→ уточняющий вопрос
```

`session_id` хранит историю диалога (in-memory checkpointer), поэтому `clarifier`
ведёт диалог через несколько запросов. Запросы пишутся в таблицу `query_log`.

## Быстрый старт

Окружение управляется через [uv](https://docs.astral.sh/uv/).

```bash
# 1. Установить зависимости (создаст .venv автоматически)
uv sync

# 2. Настроить переменные окружения
cp .env.example .env
# заполните POLZA_API_KEY (LLM) и ключи Selectel S3 (для Части 3)

# 3. Поднять базу данных (PostgreSQL в Docker)
docker-compose up -d db

# 4. Запустить API (таблицы создаются автоматически на старте)
uv run uvicorn app.main:app --reload
```

После запуска документация доступна на http://localhost:8000/docs

## Selectel S3 (Часть 3)

Работа с S3 включается автоматически, когда в `.env` заданы `SELECTEL_ACCESS_KEY`
и `SELECTEL_SECRET_KEY`. Пока ключей нет — загрузка работает, но файл в S3 не кладётся.

Чтобы включить: в панели Selectel создайте бакет (Object Storage) и сервисного
пользователя с ключами S3, впишите их и имя бакета (`SELECTEL_BUCKET`) в `.env`.

## Переменные окружения

См. [.env.example](.env.example). LLM подключается через polza.ai
(OpenAI-совместимый шлюз): `POLZA_API_KEY`, `POLZA_BASE_URL`, `LLM_MODEL`.
