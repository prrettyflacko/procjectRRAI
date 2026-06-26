import os
from dotenv import load_dotenv
load_dotenv()

from app.agents.graph1 import agent_graph1

def run_local_test():
    print("🚀 Запуск локального теста ИИ-Агента с трекингом шагов...\n")
    
    initial_state = {
        "dataset_id": 1,
        "session_id": "test-session-123",
        "question": "Какая общая выручка по заказам в Москве?",
        "sql_query": None,
        "raw_result": None,
        "final_response": None,
        "image_base64": None,
        "next_step": None,
        "agent_logs": []  # Инициализируем пустой список логов
    }
    
    try:
        final_state = agent_graph1.invoke(initial_state)
        
        print("\n🏆 ТРЕЙСИНГ АГЕНТА (АНАЛОГ LANGSMITH) В КОНСОЛИ:")
        print("="*50)
        for log in final_state.get("agent_logs", []):
            print(log)
        print("="*50)
        
        print(f"\nФинальный ответ синтезатора:\n{final_state.get('final_response')}")
        
    except Exception as e:
        print(f"\n❌ Ошибка выполнения графа: {e}")

if __name__ == "__main__":
    run_local_test()
