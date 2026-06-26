from langgraph.graph import StateGraph, END
from app.agents.state1 import AgentState
from app.agents.nodes1 import router_node, clarifier_node, sql_agent_node, synthesizer_node

# Инициализируем граф с изолированной структурой состояния (агент v2 от друга)
builder = StateGraph(AgentState)

# Регистрируем узлы
builder.add_node("router", router_node)
builder.add_node("clarifier", clarifier_node)
builder.add_node("sql_agent", sql_agent_node)
builder.add_node("synthesizer", synthesizer_node)

# Точка входа в граф
builder.set_entry_point("router")

# Условный переход из роутера
builder.add_conditional_edges(
    "router",
    lambda state: state["next_step"],
    {
        "sql_agent": "sql_agent",
        "clarifier": "clarifier",
    },
)

# Линейные переходы между узлами
builder.add_edge("sql_agent", "synthesizer")
builder.add_edge("synthesizer", END)
builder.add_edge("clarifier", END)

# Компилируем граф агента v2
agent_graph1 = builder.compile()
