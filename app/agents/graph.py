"""Сборка графа LangGraph.

Структура:

    router ──(ясно)──→ sql_agent ──→ synthesizer ──→ END
       │
       └──(неясно)──→ clarifier ──→ END

MemorySaver — это checkpointer: он хранит состояние каждой сессии в памяти по ключу
thread_id (= session_id). Благодаря ему clarifier может продолжить диалог в следующем запросе.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.nodes import clarifier, router, sql_agent, synthesizer
from app.agents.state import GraphState


def _route_after_router(state: dict) -> str:
    """Условное ребро: куда идти после router."""
    return "clarifier" if state["needs_clarification"] else "sql_agent"


def build_graph():
    builder = StateGraph(GraphState)

    builder.add_node("router", router)
    builder.add_node("clarifier", clarifier)
    builder.add_node("sql_agent", sql_agent)
    builder.add_node("synthesizer", synthesizer)

    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router",
        _route_after_router,
        {"clarifier": "clarifier", "sql_agent": "sql_agent"},
    )
    builder.add_edge("clarifier", END)
    builder.add_edge("sql_agent", "synthesizer")
    builder.add_edge("synthesizer", END)

    return builder.compile(checkpointer=MemorySaver())


# Один скомпилированный граф на всё приложение.
graph = build_graph()
