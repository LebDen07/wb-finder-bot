# bot.py
import os
import sys
import requests
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from flask import Flask
from threading import Thread
import logging
import urllib.parse

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print(f"🐍 Python: {sys.version}")

# Токен
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    logger.error("❗ TELEGRAM_TOKEN не задан")
    sys.exit(1)

# === Flask для keep-alive ===
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "🟢 Бот работает"

def run_flask():
    port = int(os.getenv('PORT', 10000))
    app_flask.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()

# === Поиск товаров — с фолбэком ===
def search_wb(query: str) -> list:
    if not query.strip():
        return []  # ✅ Исправлено: правильный отступ и возврат пустого списка

    keyword = urllib.parse.quote(query.strip())
    logger.info(f"🔍 Поиск: '{query}'")

    # 🔁 Список URL для попыток (резервные варианты)
    urls = [
        f"https://catalog.wb.ru/catalog/autosearch/data?query={keyword}&dest=-1257786&lang=ru&curr=rub",
        f"https://catalog.wb.ru/catalog/electronics/catalog?keyword={keyword}&dest=-1257786&sort=popular",
        f"https://search.wb.ru/exactmatch/ru/common/v4/search?query={keyword}&dest=-1257786&resultset=items"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.wildberries.ru/",
        "Origin": "https://www.wildberries.ru",
        "X-Requested-With": "XMLHttpRequest"
    }

    for i, url in enumerate(urls, 1):
        try:
            logger.info(f"🔁 Попытка {i}: GET {url}")
            response = requests.get(url, headers=headers, timeout=10)

            logger.info(f"📊 Статус: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.info(f"📦 JSON получен: {len(str(data))}
