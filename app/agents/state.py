"""Состояние графа LangGraph.

Состояние — это словарь, который передаётся между узлами графа. Каждый узел читает
нужные поля и возвращает изменённые.

messages хранит историю диалога (вопросы пользователя + уточнения системы). Благодаря
add_messages и checkpointer'у история накапливается между запросами с одним session_id —
так clarifier может вести многошаговый диалог.
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    messages: Annotated[list, add_messages]  # история диалога
    question: str            # текущий вопрос пользователя
    dataset_id: int          # с каким датасетом работаем
    schema: str              # перечень колонок датасета (для промптов)
    sql: str                 # сгенерированный SQL
    rows: str                # результат выполнения SQL (как текст, для синтезатора)
    result_rows: list        # результат выполнения SQL (структурой, для графиков/таблиц)
    answer: str              # финальный ответ пользователю
    needs_clarification: bool  # True — если нужен уточняющий вопрос
