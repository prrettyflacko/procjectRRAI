"""DataMind — веб-интерфейс (Streamlit) в стиле Pinterest.

Тонкий клиент: рисует UI и общается с нашим API по HTTP (requests).
Вся логика (SQL, LLM, БД) — на сервере за API.

Настройки берутся из Streamlit Secrets (на Streamlit Cloud) или из переменных
окружения (локально):
  API_URL  — адрес бэкенда, напр. http://161.104.56.45:8000
  API_KEY  — ключ для заголовка X-API-Key
"""

import hashlib
import os
import uuid

import requests
import streamlit as st

# ---------------------------------------------------------------- настройки

def _conf(key: str, default: str) -> str:
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)


API_URL = _conf("API_URL", "http://localhost:8000").rstrip("/")
API_KEY = _conf("API_KEY", "")
HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}

# Палитра градиентов для «обложек» карточек (рандомно, но стабильно по имени).
GRADIENTS = [
    ("#FF6B6B", "#FFD93D"), ("#6A11CB", "#2575FC"), ("#11998E", "#38EF7D"),
    ("#F953C6", "#B91D73"), ("#FF512F", "#DD2476"), ("#1FA2FF", "#12D8FA"),
    ("#F7971E", "#FFD200"), ("#8E2DE2", "#4A00E0"), ("#00C9FF", "#92FE9D"),
    ("#FC466B", "#3F5EFB"),
]


def _gradient(seed: str) -> tuple[str, str]:
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return GRADIENTS[h % len(GRADIENTS)]


# ---------------------------------------------------------------- API-клиент

def api_get(path: str, params: dict | None = None):
    r = requests.get(f"{API_URL}{path}", headers=HEADERS, params=params, timeout=180)
    r.raise_for_status()
    return r.json()


def api_query(payload: dict):
    r = requests.post(f"{API_URL}/query", headers=HEADERS, json=payload, timeout=300)
    r.raise_for_status()
    return r.json()


def api_upload(name: str, data: bytes):
    files = {"file": (name, data, "text/csv")}
    r = requests.post(f"{API_URL}/upload", headers=HEADERS, files=files, timeout=300)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------- страница

st.set_page_config(page_title="DataMind", page_icon="📌", layout="wide")

CSS = """
<style>
#MainMenu, footer, header {visibility: hidden;}
.stApp {background: #f4f4f6;}
.block-container {padding-top: 1.5rem; max-width: 1300px;}

/* Заголовок-бренд */
.brand {font-size: 2.2rem; font-weight: 800; color: #111;
        letter-spacing: -1px; margin-bottom: .2rem;}
.brand span {color: #E60023;}
.subtitle {color: #767676; margin-bottom: 1.2rem;}

/* Masonry-лента */
.masonry {column-count: 3; column-gap: 18px;}
@media (max-width: 1100px) {.masonry {column-count: 2;}}
@media (max-width: 700px)  {.masonry {column-count: 1;}}

.card {
  break-inside: avoid; background: #fff; border-radius: 18px;
  margin-bottom: 18px; overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,.06);
  transition: transform .18s ease, box-shadow .18s ease;
}
.card:hover {transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,.14);}
.cover {display:flex; align-items:center; justify-content:center;
        color:#fff; font-weight:800; font-size:2.4rem;}
.card-body {padding: 14px 16px 18px;}
.card-title {font-weight: 700; font-size: 1.05rem; color:#111; margin-bottom:6px;
             word-break: break-word;}
.card-meta {color:#767676; font-size:.85rem;}
.pill {display:inline-block; background:#efefef; color:#333; border-radius:999px;
       padding:3px 10px; font-size:.78rem; margin-top:8px; margin-right:6px;}
.q {font-weight:700; color:#111;}
.a {color:#333; margin-top:6px; white-space:pre-wrap;}

/* Кнопки Streamlit под Pinterest */
.stButton>button {border-radius: 999px; background:#E60023; color:#fff;
   border:none; font-weight:700; padding:.5rem 1.2rem;}
.stButton>button:hover {background:#ad081b; color:#fff;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "chat" not in st.session_state:
    st.session_state.chat = []  # список (role, text)


# ---------------------------------------------------------------- sidebar

with st.sidebar:
    st.markdown("## 📌 DataMind")
    page = st.radio(
        "Навигация",
        ["📌 Лента", "⬆️ Загрузить", "💬 Спросить", "🕘 История"],
        label_visibility="collapsed",
    )
    st.divider()
    # Статус подключения (health открыт без ключа).
    try:
        api_get("/health")
        st.success(f"API подключён\n\n{API_URL}")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Нет связи с API\n\n{API_URL}\n\n{exc}")


def render_masonry(cards_html: list[str]) -> None:
    st.markdown(f'<div class="masonry">{"".join(cards_html)}</div>',
                unsafe_allow_html=True)


def dataset_card(ds: dict) -> str:
    c1, c2 = _gradient(ds["name"])
    height = 120 + (int(hashlib.md5(ds["name"].encode()).hexdigest(), 16) % 90)
    letter = ds["name"][:1].upper()
    date = ds["created_at"][:10]
    return f"""
    <div class="card">
      <div class="cover" style="height:{height}px;
           background:linear-gradient(135deg,{c1},{c2});">{letter}</div>
      <div class="card-body">
        <div class="card-title">{ds['name']}</div>
        <div class="card-meta">📅 {date}</div>
        <span class="pill">#{ds['id']}</span>
        <span class="pill">{ds['row_count']} строк</span>
      </div>
    </div>"""


def history_card(item: dict) -> str:
    c1, c2 = _gradient(item["question"])
    date = item["created_at"][:16].replace("T", " ")
    return f"""
    <div class="card">
      <div class="cover" style="height:8px;
           background:linear-gradient(135deg,{c1},{c2});"></div>
      <div class="card-body">
        <div class="q">❓ {item['question']}</div>
        <div class="a">{item['answer']}</div>
        <span class="pill">датасет #{item['dataset_id']}</span>
        <span class="pill">{date}</span>
      </div>
    </div>"""


# ---------------------------------------------------------------- pages

if page == "📌 Лента":
    st.markdown('<div class="brand">Data<span>Mind</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Твои датасеты — спроси у них что угодно</div>',
                unsafe_allow_html=True)
    try:
        datasets = api_get("/datasets")
        if datasets:
            render_masonry([dataset_card(d) for d in datasets])
        else:
            st.info("Пока нет датасетов. Загрузи первый на вкладке «Загрузить».")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Не удалось загрузить датасеты: {exc}")


elif page == "⬆️ Загрузить":
    st.markdown('<div class="brand">Загрузить CSV</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Файл распарсится и сохранится в базе</div>',
                unsafe_allow_html=True)
    up = st.file_uploader("Выбери CSV-файл", type=["csv"])
    if up is not None and st.button("Загрузить"):
        with st.spinner("Загружаем и парсим..."):
            try:
                res = api_upload(up.name, up.getvalue())
                st.success(
                    f"Готово! Датасет #{res['dataset_id']} «{res['name']}» — "
                    f"{res['row_count']} строк."
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"Ошибка загрузки: {exc}")


elif page == "💬 Спросить":
    st.markdown('<div class="brand">Спросить у данных</div>', unsafe_allow_html=True)
    try:
        datasets = api_get("/datasets")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Не удалось загрузить датасеты: {exc}")
        datasets = []

    if not datasets:
        st.info("Сначала загрузи датасет.")
    else:
        options = {f"#{d['id']} — {d['name']}": d["id"] for d in datasets}
        chosen = st.selectbox("Датасет", list(options.keys()))
        dataset_id = options[chosen]

        # История диалога
        for role, text in st.session_state.chat:
            with st.chat_message("user" if role == "q" else "assistant"):
                st.write(text)

        question = st.chat_input("Например: какой средний чек по городам?")
        if question:
            st.session_state.chat.append(("q", question))
            with st.chat_message("user"):
                st.write(question)
            with st.chat_message("assistant"):
                with st.spinner("Думаю..."):
                    try:
                        res = api_query({
                            "dataset_id": dataset_id,
                            "question": question,
                            "session_id": st.session_state.session_id,
                        })
                        answer = res["answer"]
                        st.write(answer)
                        if res.get("sql"):
                            with st.expander("Показать SQL"):
                                st.code(res["sql"], language="sql")
                        st.session_state.chat.append(("a", answer))
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Ошибка: {exc}")


elif page == "🕘 История":
    st.markdown('<div class="brand">История запросов</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Все вопросы и ответы из query_log</div>',
                unsafe_allow_html=True)
    try:
        items = api_get("/history", params={"limit": 60})
        if items:
            render_masonry([history_card(i) for i in items])
        else:
            st.info("История пуста — задай первый вопрос.")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Не удалось загрузить историю: {exc}")
