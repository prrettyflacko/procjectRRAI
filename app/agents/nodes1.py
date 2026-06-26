import os
import json
from openai import OpenAI
from app.db.database import get_db_connection  # Возвращаем настоящий импорт БД
from app.agents.state1 import AgentState

def get_polza_client():
    return OpenAI(
        api_key=os.getenv("POLZA_API_KEY"),
        base_url=os.getenv("POLZA_BASE_URL", "https://polza.ai")
    )

def router_node(state: AgentState) -> AgentState:
    print("--- POLZA AI: ROUTER ---")
    if "agent_logs" not in state or state["agent_logs"] is None:
        state["agent_logs"] = []
    
    state["agent_logs"].append("🎯 **Узел [Router]**: Анализирую структуру запроса пользователя...")
    client = get_polza_client()
    
    system_prompt = """Ты — маршрутизатор. Определи, нужны ли для ответа на вопрос пользователя данные из таблицы. 
    Верни строго одно слово: 'sql_agent' (если нужны данные, выручка, города, заказы) или 'clarifier' (если это приветствие или абстрактный вопрос).
    Не пиши никаких объяснений, только нужное слово."""
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt}, 
                {"role": "user", "content": state["question"]}
            ],
            temperature=0.0
        )
        
        raw_text = response.choices[0].message.content.strip().lower()
        
        if "sql" in raw_text or "agent" in raw_text:
            state["next_step"] = "sql_agent"
        else:
            state["next_step"] = "clarifier"
            
        state["agent_logs"].append(f"➡️ **Логика разветвления**: Направляю запрос в узел `{state['next_step']}`.")
    except Exception as e:
        state["next_step"] = "clarifier"
        state["agent_logs"].append(f"❌ **Ошибка Роутера**: {str(e)}. Переключаюсь на clarifier.")
        
    return state

def clarifier_node(state: AgentState) -> AgentState:
    print("--- POLZA AI: CLARIFIER ---")
    state["agent_logs"].append("❓ **Узел [Clarifier]**: Запрос не связан с метриками датасета. Готовлю вежливый ответ-уточнение.")
    state["final_response"] = "Уточните, пожалуйста, за какой период или по какому городу вы хотите посмотреть данные?"
    return state

def sql_agent_node(state: AgentState) -> AgentState:
    print("--- POLZA AI: SQL AGENT ---")
    state["agent_logs"].append("🔧 **Узел [SQL Agent]**: Запрос перехвачен. Изучаю схему PostgreSQL JSONB для генерации кода...")
    client = get_polza_client()
    
    system_prompt = f"""Ты — эксперт по SQL в PostgreSQL. Напиши SQL-запрос для таблицы `dataset_rows` (WHERE dataset_id = {state['dataset_id']}).
    Данные CSV лежат в JSONB-колонке `row_data`. Схема ключей:
    - order_id (int) -> (row_data->>'order_id')::int
    - date (text) -> row_data->>'date'
    - city (text) -> row_data->>'city'
    - category (text) -> row_data->>'category'
    - total (numeric) -> (row_data->>'total')::numeric
    Возвращай ТОЛЬКО чистый текст SQL-запроса без markdown-разметки (без ```sql)."""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt}, 
                {"role": "user", "content": state["question"]}
            ],
            temperature=0.0
        )
        generated_sql = response.choices[0].message.content.strip()
        state["sql_query"] = generated_sql
        state["agent_logs"].append(f"📝 **Сгенерированный SQL-код**:\n```sql\n{generated_sql}\n```")

        state["agent_logs"].append("💾 **[БД PostgreSQL]**: Подключаюсь и выполняю полученный SQL-запрос...")
        
        # НАСТОЯЩЕЕ ПОДКЛЮЧЕНИЕ К БАЗЕ
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(generated_sql)
        
        raw_data = cursor.fetchall()
        state["raw_result"] = json.dumps(raw_data, ensure_ascii=False)
        state["agent_logs"].append(f"📊 **Сырой ответ базы данных**: `{state['raw_result']}`")
        
        cursor.close()
        conn.close()
    except Exception as e:
        state["raw_result"] = f"Ошибка: {str(e)}"
        state["agent_logs"].append(f"❌ **Ошибка СУБД**: {str(e)}")
    return state

def synthesizer_node(state: AgentState) -> AgentState:
    print("--- POLZA AI: SYNTHESIZER ---")
    state["agent_logs"].append("🧠 **Узел [Synthesizer]**: Формирую финальный бизнес-вывод для пользователя...")
    client = get_polza_client()
    system_prompt = "Сформулируй красивый и понятный ответ пользователю на основе его вопроса и сырых данных из БД."
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Вопрос: {state['question']}\nДанные из БД: {state['raw_result']}"}
            ]
        )
        state["final_response"] = response.choices[0].message.content.strip()
        state["agent_logs"].append("✅ **Анализ успешно завершен**! Ответ передан на экран.")
    except Exception as e:
        state["final_response"] = f"Не удалось собрать ответ из-за ошибки: {str(e)}"
    return state
