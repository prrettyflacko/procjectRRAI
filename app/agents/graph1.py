from langgraph.graph import StateGraph, END
from app.agents.state1 import AgentState
from app.agents.nodes1 import router_node, clarifier_node, sql_agent_node, synthesizer_node

# Инициализируем граф с твоей изолированной структурой состояния
builder = StateGraph(AgentState)

# Регистрируем твои узлы
builder.add_node("router", router_node)
builder.add_node("clarifier", clarifier_node)
builder.add_node("sql_agent", sql_agent_node)
builder.add_node("synthesizer", synthesizer_node)

# Устанавливаем точку входа в граф
builder.set_entry_point("router")

# Настраиваем условный переход (Conditional Edge) из роутера
builder.add_conditional_edges(
    "router",
    lambda state: state["next_step"],
    {
        "sql_agent": "sql_agent",
        "clarifier": "clarifier"
    }
)

# Настраиваем линейные переходы между узлами
builder.add_edge("sql_agent", "synthesizer")
builder.add_edge("synthesizer", END)
builder.add_edge("clarifier", END)

# Компилируем твой уникальный граф
agent_graph1 = builder.compile()
