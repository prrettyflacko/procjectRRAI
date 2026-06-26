"""Эндпоинт Части 2: вопрос к данным через граф LangGraph.

POST /query — принимает вопрос, прогоняет его через граф агентов и возвращает ответ.
Каждый вопрос и ответ сохраняются в таблицу query_log.
"""

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.graph import graph
from app.db.database import get_db
from app.db.models import Dataset, DatasetRow, QueryLog
from app.schemas import QueryRequest, QueryResponse

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
    )
