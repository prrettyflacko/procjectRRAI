import streamlit as st
import requests
import uuid
import json

# Настройка футуристичного темного стиля и разметки страницы
st.set_page_config(
    page_title="DataMind Analytics Core v1",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Кастомные CSS стили для эффекта неонового терминала
st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1f2937;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 20px;
        color: #9ca3af;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
        font-weight: bold;
    }
    .terminal-card {
        background-color: #0f172a;
        border-left: 4px solid #3b82f6;
        padding: 15px;
        border-radius: 0 8px 8px 0;
        font-family: 'Courier New', Courier, monospace;
        color: #e2e8f0;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .terminal-success { border-left-color: #10b981; }
    .terminal-error { border-left-color: #ef4444; }
    .terminal-code { border-left-color: #a855f7; background-color: #1e1b4b; }
</style>
""", unsafe_index=True)

# Инициализация уникальной сессии чата и истории
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "current_logs" not in st.session_state:
    st.session_state["current_logs"] = []

# --- БОКОВАЯ ПАНЕЛЬ НАСТРОЕК ---
with st.sidebar:
    st.title("⚡ DataMind System")
    st.subheader("Управление ИИ-Ядром")
    
    # Твой персональный переключатель, жестко зашитый на твой бэкенд
    st.info("🌐 Подключено к вашему облачному серверу Selectel")
    
    st.markdown("---")
    dataset_id = st.number_input("Идентификатор датасета (Dataset ID):", min_value=1, value=1, step=1)
    
    st.markdown("---")
    st.caption(f"**Текущая сессия (UUID):**\n`{st.session_state['session_id']}`")

# --- ОСНОВНОЙ ФУТУРИСТИЧНЫЙ ИНТЕРФЕЙС ---
st.title("📊 DataMind — Интеллектуальный Аналитик")
st.caption("DeepSeek-Chat + LangGraph Agentic Pipeline v1.0")

# Создаем две кастомные вкладки
tab_chat, tab_tracing = st.tabs(["💬 Интеллектуальный Анализ", "🔍 Трейсинг Мыслей Агента (Live Logs)"])

with tab_chat:
    # Контейнер для отображения истории сообщений в стиле чата
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant" and "sql" in msg and msg["sql"]:
                with st.expander("🛠 Просмотреть исполненный SQL-код"):
                    st.code(msg["sql"], language="sql")

    # Поле ввода текстового запроса
    if user_query := st.chat_input("Задайте аналитический вопрос по вашему CSV датасету..."):
        # Сохраняем и выводим вопрос пользователя
        st.session_state["chat_history"].append({"role": "user", content: user_query})
        with st.chat_message("user"):
            st.write(user_query)
            
        # Формируем Payload. Адрес бэкенда пока локальный, на сервере поменяем на твой IP
        backend_url = "http://localhost:8000/query"
        payload = {
            "dataset_id": dataset_id,
            "question": user_query,
            "session_id": st.session_state["session_id"],
            "agent_version": "my_agent"
        }
        
        with st.chat_message("assistant"):
            with st.spinner("Агент выполняет многошаговый анализ..."):
                try:
                    response = requests.post(backend_url, json=payload, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        
                        answer = data.get("answer")
                        sql_generated = data.get("sql_generated")
                        # Принимаем пошаговые логи из твоего обновленного бэкенда!
                        logs = data.get("agent_logs", [])
                        
                        # Обновляем состояние логов и выводим ответ
                        st.session_state["current_logs"] = logs
                        st.write(answer)
                        
                        if sql_generated:
                            with st.expander("🛠 Просмотреть исполненный SQL-код"):
                                st.code(sql_generated, language="sql")
                                
                        # Сохраняем в общую историю
                        st.session_state["chat_history"].append({
                            "role": "assistant",
                            "content": answer,
                            "sql": sql_generated
                        })
                    else:
                        st.error(f"Бэкенд вернул ошибку кода: {response.status_code}")
                except Exception as e:
                    st.error(f"Не удалось отправить запрос на бэкенд: {str(e)}")

with tab_tracing:
    st.subheader("⛓️ Пошаговый трейсинг цепочки рассуждений (Agent Trace)")
    st.markdown("Здесь выводится детальная трассировка работы LangGraph графа в режиме реального времени — аналог платформы **LangSmith**.")
    
    if st.session_state["current_logs"]:
        st.markdown("---")
        for log in st.session_state["current_logs"]:
            # Кастомный парсинг и рендеринг логов в зависимости от их содержимого
            if "❌" in log:
                st.markdown(f'<div class="terminal-card terminal-error">{log}</div>', unsafe_index=True)
            elif "📝" in log:
                # Если в логе лежит сгенерированный SQL-код
                st.markdown('<div class="terminal-card terminal-code">📝 <b>Сгенерированный SQL-код:</b></div>', unsafe_index=True)
                # Вычленяем сам SQL (он завернут в блоки ```sql ... ```)
                clean_sql = log.replace("📝 **Сгенерированный SQL-код**:\n```sql\n", "").replace("\n```", "")
                st.code(clean_sql, language="sql")
            elif "➡️" in log:
                st.markdown(f'<div class="terminal-card terminal-success">{log}</div>', unsafe_index=True)
            else:
                st.markdown(f'<div class="terminal-card">{log}</div>', unsafe_index=True)
    else:
        st.info("Процесс рассуждений пуст. Задайте вопрос в чате, чтобы запустить трассировку агента.")
