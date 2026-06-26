import base64
import io
import matplotlib
matplotlib.use('Agg')  # Отключаем GUI-окна для корректной работы в фоне
import matplotlib.pyplot as plt
import pandas as pd

def generate_plot_base64(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> str:
    """Генерирует график и возвращает его в формате base64 строки"""
    plt.figure(figsize=(8, 4))
    plt.bar(df[x_col], df[y_col], color='skyblue')
    plt.title(title)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return f"data:image/png;base64,{img_base64}"
