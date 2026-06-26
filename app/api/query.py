"""Эндпоинт Части 2: вопрос к данным через граф LangGraph.

POST /query — принимает вопрос, прогоняет его через граф агентов и возвращает ответ.
Каждый вопрос и ответ сохраняются в таблицу query_log.
"""

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.graph import graph
from app.agents.graph1 import agent_graph1
from app.db.database import get_db
from app.db.models import Dataset, DatasetRow, QueryLog
from app.schemas import Query2Response, QueryLogOut, QueryRequest, QueryResponse

router = APIRouter(tags=["query"])


def _get_schema(db: Session, dataset_id: int) -> str:
    """Возвращает список колонок датасета (имена ключей первой строки)."""
    first_row = db.scalars(
        select(DatasetRow)
        .where(DatasetRow.dataset_id == dataset_id)
        .order_by(DatasetRow.row_index)
        .limit(1)
    ).first()
    if first_row is None:
        return ""
    return ", ".join(first_row.row_data.keys())


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, db: Session = Depends(get_db)) -> QueryResponse:
    if db.get(Dataset, req.dataset_id) is None:
        raise HTTPException(status_code=404, detail="Датасет не найден")

    schema = _get_schema(db, req.dataset_id)
    if not schema:
        raise HTTPException(status_code=400, detail="В датасете нет строк")

    # Запускаем граф. thread_id = session_id — так сохраняется история диалога.
    result = graph.invoke(
        {
            "messages": [HumanMessage(content=req.question)],
            "question": req.question,
            "dataset_id": req.dataset_id,
            "schema": schema,
        },
        config={"configurable": {"thread_id": req.session_id}},
    )

    answer = result["answer"]

    # Сохраняем вопрос и ответ в историю.
    db.add(QueryLog(dataset_id=req.dataset_id, question=req.question, answer=answer))
    db.commit()

    return QueryResponse(
        answer=answer,
        needs_clarification=result.get("needs_clarification", False),
        sql=result.get("sql"),
        result_rows=result.get("result_rows", []),
    )


@router.post("/query2", response_model=Query2Response)
def query2(req: QueryRequest, db: Session = Depends(get_db)) -> Query2Response:
    """Агент v2 (от друга): отдельный граф с пошаговыми логами."""
    if db.get(Dataset, req.dataset_id) is None:
        raise HTTPException(status_code=404, detail="Датасет не найден")

    result = agent_graph1.invoke({
        "dataset_id": req.dataset_id,
        "session_id": req.session_id,
        "question": req.question,
        "agent_logs": [],
    })

    answer = result.get("final_response") or "Не удалось получить ответ."
    # Историю пишем в общий query_log — данные-то одни.
    db.add(QueryLog(dataset_id=req.dataset_id, question=req.question, answer=answer))
    db.commit()

    return Query2Response(
        answer=answer,
        sql=result.get("sql_query"),
        logs=result.get("agent_logs", []),
    )


@router.get("/history", response_model=list[QueryLogOut])
def history(
    dataset_id: int | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[QueryLog]:
    """Возвращает историю вопросов/ответов (опционально по датасету)."""
    stmt = select(QueryLog).order_by(QueryLog.created_at.desc()).limit(limit)
    if dataset_id is not None:
        stmt = stmt.where(QueryLog.dataset_id == dataset_id)
    return list(db.scalars(stmt))
