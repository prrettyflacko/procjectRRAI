"""DataMind — веб-интерфейс (Streamlit) в пастельном стиле Pinterest.

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
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

MSK = ZoneInfo("Europe/Moscow")


def to_msk(iso: str, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Время из API хранится в UTC — показываем в московском времени."""
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(MSK).strftime(fmt)
    except Exception:
        return iso[:16]

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

# Пастельные «мужские» градиенты для обложек (сталь/шалфей/камень/деним).
GRADIENTS = [
    ("#C6D3DE", "#DCE4EA"), ("#CBD9CE", "#E2E8DD"), ("#BFD7D4", "#DCE9E6"),
    ("#C3CCD9", "#DDE3EC"), ("#D8D2C6", "#EAE5DB"), ("#D0D4C0", "#E4E6D8"),
    ("#BCC9D6", "#D6DEE6"), ("#C2D2D2", "#DBE6E4"), ("#CFD3D6", "#E5E8EA"),
    ("#C4CFDD", "#DBE2EC"),
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


def api_query2(payload: dict):
    r = requests.post(f"{API_URL}/query2", headers=HEADERS, json=payload, timeout=300)
    r.raise_for_status()
    return r.json()


def api_upload(name: str, data: bytes):
    files = {"file": (name, data, "text/csv")}
    r = requests.post(f"{API_URL}/upload", headers=HEADERS, files=files, timeout=300)
    r.raise_for_status()
    return r.json()


def api_delete(dataset_id: int):
    r = requests.delete(f"{API_URL}/datasets/{dataset_id}", headers=HEADERS, timeout=60)
    r.raise_for_status()


# ---------------------------------------------------------------- страница

st.set_page_config(page_title="DataMind", page_icon="📊", layout="wide")

CSS = """
<style>
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 1.2rem; max-width: 1280px;}

/* Шапка-бренд */
.brand {font-size: 2.4rem; font-weight: 800; color:#33404A;
        letter-spacing:-1px; margin-bottom:.1rem;}
.brand span {color:#5E7E92;}
.subtitle {color:#8795A0; margin-bottom:.6rem; font-size:1rem;}

/* Вкладки покрупнее и помягче */
.stTabs [data-baseweb="tab-list"] {gap: 8px;}
.stTabs [data-baseweb="tab"] {
  background:#E8ECEC; border-radius:999px; padding:8px 18px; font-weight:600;
}
.stTabs [aria-selected="true"] {background:#5E7E92 !important; color:#fff !important;}

/* Masonry-лента */
.masonry {column-count: 3; column-gap: 18px; margin-top: 6px;}
@media (max-width: 1100px) {.masonry {column-count: 2;}}
@media (max-width: 700px)  {.masonry {column-count: 1;}}

.card {
  break-inside: avoid; background:#fff; border-radius:22px;
  margin-bottom:18px; overflow:hidden; box-shadow:0 2px 10px rgba(60,75,90,.10);
  transition: transform .18s ease, box-shadow .18s ease;
}
.card:hover {transform: translateY(-4px); box-shadow:0 10px 26px rgba(60,75,90,.20);}
.cover {display:flex; align-items:center; justify-content:center;
        color:rgba(51,64,74,.55); font-weight:800; font-size:2.6rem;}
.card-body {padding:14px 18px 18px;}
.card-title {font-weight:700; font-size:1.05rem; color:#33404A; margin-bottom:6px;
             word-break:break-word;}
.card-meta {color:#8795A0; font-size:.85rem;}
.pill {display:inline-block; background:#E8ECEC; color:#5A6670; border-radius:999px;
       padding:3px 11px; font-size:.78rem; margin-top:8px; margin-right:6px;}
.q {font-weight:700; color:#33404A;}
.a {color:#4F5963; margin-top:6px; white-space:pre-wrap;}

/* Чат-бабблы (свои, чтобы текст был точно виден) */
.bubble {border-radius:18px; padding:12px 16px; margin:8px 0; max-width:85%;
         line-height:1.45;}
.bubble-user {background:#D3DEE8; color:#2E3A44; margin-left:auto;
              border-bottom-right-radius:4px;}
.bubble-ai {background:#D7E3DD; color:#2E3A3A; margin-right:auto;
            border-bottom-left-radius:4px;}
.bubble .who {font-size:.78rem; font-weight:700; opacity:.7; margin-bottom:3px;}

.stButton>button {border-radius:999px; background:#5E7E92; color:#fff;
   border:none; font-weight:700; padding:.5rem 1.4rem;}
.stButton>button:hover {background:#4d6a7c; color:#fff;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "chat" not in st.session_state:
    st.session_state.chat = []  # список (role, text, sql)
if "chat2" not in st.session_state:
    st.session_state.chat2 = []  # диалог агента 2: (role, text, sql, logs)


# ---------------------------------------------------------------- helpers

def render_masonry(cards_html: list[str]) -> None:
    st.markdown(f'<div class="masonry">{"".join(cards_html)}</div>',
                unsafe_allow_html=True)


def dataset_card(ds: dict) -> str:
    c1, c2 = _gradient(ds["name"])
    height = 120 + (int(hashlib.md5(ds["name"].encode()).hexdigest(), 16) % 90)
    letter = ds["name"][:1].upper()
    date = to_msk(ds["created_at"], "%Y-%m-%d")
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
    date = to_msk(item["created_at"]) + " МСК"
    ans = (item["answer"] or "").replace("<", "&lt;").replace(">", "&gt;")
    q = (item["question"] or "").replace("<", "&lt;").replace(">", "&gt;")
    return f"""
    <div class="card">
      <div class="cover" style="height:10px;
           background:linear-gradient(135deg,{c1},{c2});"></div>
      <div class="card-body">
        <div class="q">❓ {q}</div>
        <div class="a">{ans}</div>
        <span class="pill">датасет #{item['dataset_id']}</span>
        <span class="pill">{date}</span>
      </div>
    </div>"""


# ---------------------------------------------------------------- шапка

col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown('<div class="brand">Data<span>Mind</span> 📊</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Загрузи данные и спроси у них что угодно</div>',
                unsafe_allow_html=True)
with col_status:
    try:
        api_get("/health")
        st.success("API на связи", icon="✅")
    except Exception:  # noqa: BLE001
        st.error("Нет связи с API", icon="⚠️")

def render_bubble(role: str, text: str) -> None:
    who = "Ты" if role == "user" else "🤖 DataMind"
    cls = "bubble-user" if role == "user" else "bubble-ai"
    safe = (text or "").replace("<", "&lt;").replace(">", "&gt;")
    st.markdown(
        f'<div class="bubble {cls}"><div class="who">{who}</div>{safe}</div>',
        unsafe_allow_html=True,
    )


def render_result(rows: list) -> None:
    """Если результат табличный — показываем график (по категориальной + числовой
    колонке) и саму таблицу."""
    if not rows or len(rows) < 2:
        return
    try:
        df = pd.DataFrame(rows)
    except Exception:  # noqa: BLE001
        return
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    labels = [c for c in df.columns if c not in numeric]
    if numeric and labels:
        with st.expander("📊 График", expanded=True):
            st.bar_chart(df.set_index(labels[0])[numeric])
    with st.expander("📋 Данные"):
        st.dataframe(df, use_container_width=True)


# Навигация одной строкой (одна страница за раз — чтобы chat_input прилипал к низу).
nav = st.segmented_control(
    "nav",
    ["🗂 Датасеты", "⬆️ Загрузить", "🤖 Агент 1", "🧪 Агент 2", "🕘 История"],
    default="🗂 Датасеты",
    label_visibility="collapsed",
) or "🗂 Датасеты"


# ---------------------------------------------------------------- Загрузить

if nav == "⬆️ Загрузить":
    st.write("#### Загрузить CSV")
    up = st.file_uploader("Выбери CSV-файл", type=["csv"])
    if up is not None and st.button("Загрузить", key="upload_btn"):
        with st.spinner("Загружаем и парсим..."):
            try:
                res = api_upload(up.name, up.getvalue())
                st.success(
                    f"Готово! Датасет #{res['dataset_id']} «{res['name']}» — "
                    f"{res['row_count']} строк."
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"Ошибка загрузки: {exc}")


# ---------------------------------------------------------------- Агент 1

elif nav == "🤖 Агент 1":
    try:
        datasets = api_get("/datasets")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Не удалось загрузить датасеты: {exc}")
        datasets = []

    if not datasets:
        st.info("Сначала загрузи датасет.")
    else:
        options = {f"#{d['id']} — {d['name']}": d["id"] for d in datasets}
        col_ds, col_clear = st.columns([4, 1])
        with col_ds:
            chosen = st.selectbox("Датасет", list(options.keys()))
        dataset_id = options[chosen]
        with col_clear:
            st.write("")
            if st.session_state.chat and st.button("Очистить", key="clear_chat"):
                st.session_state.chat = []
                st.session_state.session_id = str(uuid.uuid4())
                st.rerun()

        # Уже накопленный диалог (сверху вниз).
        for role, text, sql, rows in st.session_state.chat:
            render_bubble(role, text)
            if rows:
                render_result(rows)
            if sql:
                with st.expander("Показать SQL"):
                    st.code(sql, language="sql")

        # Поле ввода закреплено внизу страницы (как в мессенджерах).
        prompt = st.chat_input("Например: какой средний чек по городам?")
        if prompt and prompt.strip():
            render_bubble("user", prompt)
            st.session_state.chat.append(("user", prompt, None, None))
            try:
                with st.spinner("Думаю над данными..."):
                    res = api_query({
                        "dataset_id": dataset_id,
                        "question": prompt,
                        "session_id": st.session_state.session_id,
                    })
                answer, sql = res["answer"], res.get("sql")
                rows = res.get("result_rows", [])
            except Exception as exc:  # noqa: BLE001
                answer, sql, rows = f"Ошибка: {exc}", None, []
            render_bubble("ai", answer)
            if rows:
                render_result(rows)
            if sql:
                with st.expander("Показать SQL"):
                    st.code(sql, language="sql")
            st.session_state.chat.append(("ai", answer, sql, rows))


# ---------------------------------------------------------------- Агент 2 (друга)

elif nav == "🧪 Агент 2":
    st.caption("Альтернативный агент (версия друга) — с пошаговыми логами работы.")
    try:
        datasets = api_get("/datasets")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Не удалось загрузить датасеты: {exc}")
        datasets = []

    if not datasets:
        st.info("Сначала загрузи датасет.")
    else:
        options = {f"#{d['id']} — {d['name']}": d["id"] for d in datasets}
        col_ds, col_clear = st.columns([4, 1])
        with col_ds:
            chosen = st.selectbox("Датасет", list(options.keys()), key="ds2")
        dataset_id = options[chosen]
        with col_clear:
            st.write("")
            if st.session_state.chat2 and st.button("Очистить", key="clear_chat2"):
                st.session_state.chat2 = []
                st.rerun()

        for role, text, sql, logs in st.session_state.chat2:
            render_bubble(role, text)
            if logs:
                with st.expander("🔍 Логи агента"):
                    for line in logs:
                        st.markdown(line)
            if sql:
                with st.expander("Показать SQL"):
                    st.code(sql, language="sql")

        prompt = st.chat_input("Спроси агента 2...", key="ci2")
        if prompt and prompt.strip():
            render_bubble("user", prompt)
            st.session_state.chat2.append(("user", prompt, None, None))
            try:
                with st.spinner("Агент 2 работает..."):
                    res = api_query2({
                        "dataset_id": dataset_id,
                        "question": prompt,
                        "session_id": st.session_state.session_id,
                    })
                answer, sql, logs = res["answer"], res.get("sql"), res.get("logs", [])
            except Exception as exc:  # noqa: BLE001
                answer, sql, logs = f"Ошибка: {exc}", None, []
            render_bubble("ai", answer)
            if logs:
                with st.expander("🔍 Логи агента"):
                    for line in logs:
                        st.markdown(line)
            if sql:
                with st.expander("Показать SQL"):
                    st.code(sql, language="sql")
            st.session_state.chat2.append(("ai", answer, sql, logs))


# ---------------------------------------------------------------- История

elif nav == "🕘 История":
    try:
        items = api_get("/history", params={"limit": 60})
        if items:
            render_masonry([history_card(i) for i in items])
        else:
            st.info("История пуста — задай первый вопрос.")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Не удалось загрузить историю: {exc}")


# ---------------------------------------------------------------- Датасеты (default)

else:
    try:
        datasets = api_get("/datasets")
        if datasets:
            render_masonry([dataset_card(d) for d in datasets])
            with st.expander("🗑 Управление датасетами"):
                opts = {f"#{d['id']} — {d['name']}": d["id"] for d in datasets}
                to_del = st.multiselect("Выбери, что удалить", list(opts.keys()))
                if to_del and st.button("Удалить выбранные", key="del_btn"):
                    with st.spinner("Удаляем..."):
                        for label in to_del:
                            api_delete(opts[label])
                    st.success("Удалено")
                    st.rerun()
        else:
            st.info("Пока нет датасетов. Загрузи первый на вкладке «Загрузить».")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Не удалось загрузить датасеты: {exc}")
