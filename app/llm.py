"""Клиент LLM.

Мы используем polza.ai — это OpenAI-совместимый шлюз: тот же протокол, что у OpenAI,
только другой base_url. Поэтому подключаемся через ChatOpenAI из langchain-openai,
подставляя ключ и адрес polza.ai.
"""

from langchain_openai import ChatOpenAI

from app.config import settings


def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    """Возвращает настроенный клиент LLM.

    temperature=0 — для предсказуемых ответов (важно при генерации SQL).
    """
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.POLZA_API_KEY,
        base_url=settings.POLZA_BASE_URL,
        temperature=temperature,
    )
