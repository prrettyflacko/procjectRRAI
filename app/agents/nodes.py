"""Узлы графа агентов.

Каждый узел — это обычная функция: принимает состояние (dict), возвращает изменённые поля.

  router      — решает: вопрос ясен (→ sql_agent) или нужно уточнение (→ clarifier).
  clarifier   — формулирует уточняющий вопрос и завершает диалог до следующего сообщения.
  sql_agent   — генерирует SQL по вопросу, выполняет его в БД, кладёт результат.
  synthesizer — превращает сырой результат в человекочитаемый ответ.
"""

from langchain_core.messages import AIMessage
from sqlalchemy import text

from app.db.database import SessionLocal
from app.llm import get_llm

llm = get_llm()


def router(state: dict) -> dict:
    """Определяет, достаточно ли информации в диалоге для генерации SQL."""
    system = (
        "Ты — маршрутизатор запросов к данным. Таблица содержит колонки: "
        f"{state['schema']}.\n"
        "Учитывай всю историю диалога (включая твои прошлые уточнения и ответы пользователя).\n"
        "Большинство вопросов про данные можно посчитать SQL-запросом — по умолчанию выбирай SQL.\n"
        "Отсутствие периода, города или иной детали — НЕ повод переспрашивать: считай по всем данным.\n"
        "- Вопрос можно выразить запросом по колонкам — ответь ровно: SQL\n"
        "- Это приветствие/болтовня или совсем непонятно, что считать — ответь ровно: CLARIFY\n"
        "Ответь ОДНИМ словом, без пояснений."
    )
    # Передаём всю историю диалога, а не только последний вопрос.
    decision = llm.invoke(
        [("system", system), *state["messages"]]
    ).content.strip().upper()

    needs_clarification = "CLARIFY" in decision
    return {"needs_clarification": needs_clarification}


def clarifier(state: dict) -> dict:
    """Задаёт один уточняющий вопрос (диалог продолжится следующим запросом сессии)."""
    system = (
        "Вопрос пользователя к данным неоднозначен. Колонки таблицы: "
        f"{state['schema']}.\n"
        "Учитывай всю историю диалога. Задай ОДИН короткий уточняющий вопрос на русском, "
        "чтобы понять, что именно посчитать. Не отвечай на сам вопрос."
    )
    question = llm.invoke(
        [("system", system), *state["messages"]]
    ).content.strip()

    return {
        "answer": question,
        "needs_clarification": True,
        "messages": [AIMessage(content=question)],
    }


def _clean_sql(raw: str) -> str:
    """Убирает markdown-обёртку ```sql ... ``` и лишние пробелы."""
    sql = raw.strip()
    if sql.startswith("```"):
        sql = sql.split("```")[1]
        if sql.lower().startswith("sql"):
            sql = sql[3:]
    return sql.strip().rstrip(";").strip()


def _run_sql(sql: str) -> tuple[str, str | None]:
    """Выполняет SELECT. Возвращает (результат_как_текст, текст_ошибки|None)."""
    if not sql.lower().startswith(("select", "with")):
        return "", "разрешён только SELECT-запрос"

    db = SessionLocal()
    try:
        result = db.execute(text(sql)).mappings().all()
        return str([dict(r) for r in result]), None
    except Exception as exc:  # noqa: BLE001 — текст ошибки вернём для самоисправления
        return "", str(exc)
    finally:
        db.close()


def _column_value_hints(dataset_id: int, columns: list[str], max_distinct: int = 30) -> list[str]:
    """Возвращает реальные значения категориальных колонок (где их мало).

    Нужно, чтобы агент фильтровал по НАСТОЯЩИМ значениям из базы, а не выдумывал
    («СПб» вместо «Санкт-Петербург»). Колонки с большим числом значений пропускаем.
    """
    db = SessionLocal()
    hints: list[str] = []
    try:
        for col in columns:
            rows = db.execute(
                text(
                    "SELECT DISTINCT row_data->>:c AS v FROM dataset_rows "
                    "WHERE dataset_id = :d LIMIT :lim"
                ),
                {"c": col, "d": dataset_id, "lim": max_distinct + 1},
            ).all()
            vals = [r[0] for r in rows if r[0] is not None]
            if 0 < len(vals) <= max_distinct:
                hints.append(f"- {col}: {', '.join(map(str, vals))}")
    finally:
        db.close()
    return hints


def sql_agent(state: dict) -> dict:
    """Генерирует SQL по вопросу и выполняет его. При ошибке — одна попытка исправления."""
    columns = [c.strip() for c in state["schema"].split(",") if c.strip()]
    hints = _column_value_hints(state["dataset_id"], columns)
    hints_block = ""
    if hints:
        hints_block = (
            "Реальные значения категориальных колонок (используй ТОЛЬКО их):\n"
            + "\n".join(hints) + "\n"
            "Если пользователь написал синоним или сокращение (например, 'СПб', 'спб', "
            "'питер'), сопоставь его с ближайшим по смыслу значением из списка "
            "('Санкт-Петербург'). Никогда не придумывай значения, которых нет в списке.\n"
        )
    system = (
        "Ты пишешь ОДИН SQL-запрос для PostgreSQL.\n"
        "Данные лежат в таблице dataset_rows: каждая строка исходного CSV хранится в "
        "JSONB-колонке row_data.\n"
        "Доступ к полю: row_data->>'имя_колонки'. Значения всегда текстовые, поэтому числа "
        "приводи через ::numeric, даты через ::date.\n"
        "ВАЖНО: row_data есть только в таблице dataset_rows. В подзапросах обращайся к "
        "колонкам по их алиасам, а не к row_data снова.\n"
        f"Доступные колонки внутри row_data: {state['schema']}.\n"
        + hints_block
        + f"ОБЯЗАТЕЛЬНО добавь условие WHERE dataset_id = {state['dataset_id']}.\n"
        "Учитывай всю историю диалога (вопрос пользователя и уточнения).\n"
        "Используй только SELECT. Верни ТОЛЬКО SQL, без пояснений и без markdown."
    )
    sql = _clean_sql(
        llm.invoke([("system", system), *state["messages"]]).content
    )
    rows, error = _run_sql(sql)

    # Самоисправление: если SQL упал, отдаём модели текст ошибки и просим починить (1 раз).
    if error is not None:
        fix_prompt = (
            f"Этот SQL завершился ошибкой:\n{sql}\n\nТекст ошибки: {error}\n\n"
            "Исправь запрос. Верни ТОЛЬКО исправленный SQL без пояснений."
        )
        sql = _clean_sql(
            llm.invoke([("system", system), ("user", fix_prompt)]).content
        )
        rows, error = _run_sql(sql)

    if error is not None:
        rows = f"ОШИБКА выполнения SQL: {error}"

    return {"sql": sql, "rows": rows}


def synthesizer(state: dict) -> dict:
    """Формирует финальный человекочитаемый ответ из результата SQL."""
    system = (
        "Ты формулируешь краткий понятный ответ на русском по результату SQL-запроса.\n"
        "Если результат пустой — скажи, что данных нет. Если в результате ошибка — "
        "вежливо сообщи, что не удалось посчитать."
    )
    user = f"Вопрос: {state['question']}\nРезультат запроса: {state['rows']}"
    answer = llm.invoke([("system", system), ("user", user)]).content.strip()

    return {"answer": answer, "messages": [AIMessage(content=answer)]}
