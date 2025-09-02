# bot.py
import os
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction  # ✅ Правильный импорт
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from flask import Flask
from threading import Thread
import logging
import urllib.parse
import time

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === Токены и настройки ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # Опционально, для ИИ

# 🔗 Ссылки
CHANNEL_LINK = "https://t.me/+uGrNl01GXGI4NjI6"
SEARCH_BASE = "https://www.wildberries.ru/catalog/0/search.aspx?"

# Проверка токена
if not TELEGRAM_TOKEN:
    logger.error("❗ TELEGRAM_TOKEN не задан. Установите в переменных окружения Render.")
else:
    logger.info("✅ TELEGRAM_TOKEN загружен")

# === Flask для поддержания активности (чтобы Render не "убил" процесс) ===
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "✅ Бот работает 24/7"

def run():
    port = int(os.getenv('PORT', 8080))
    app_flask.run(host='0.0.0.0', port=port)

def keep_alive():
    logger.info("🚀 Запускаем Flask-сервер для поддержания активности...")
    t = Thread(target=run)
    t.daemon = True
    t.start()

# === Состояние пользователя (опционально) ===
user_data = {}

# === Генерация ссылки с фильтрами ===
def build_wb_link(query: str, rating: str = "4.7", sort: str = "popular", max_price: str = None) -> str:
    params = {
        "search": query,
        "sort": sort,
        "rating": rating.replace("от ", "")
    }
    if max_price:
        # Фильтр по цене: 0 до max_price
        params["priceU"] = f"0;{max_price}"
    encoded = urllib.parse.urlencode(params)
    return f"https://www.wildberries.ru/catalog/0/search.aspx?{encoded}"

# === Пример топ-5 ссылок (можно заменить на API позже) ===
def get_top5_links(query: str) -> list:
    base = query.replace(" ", "+")
    return [
        {
            "name": f"🔥 {query.capitalize()} — Лидер продаж",
            "price": 2999,
            "reviews": 150,
            "link": build_wb_link(base, "4.7")
        },
        {
            "name": f"💎 {query.capitalize()} — Премиум версия",
            "price": 4599,
            "reviews": 98,
            "link": build_wb_link(base, "4.8")
        },
        {
            "name": f"💰 {query.capitalize()} — Бюджетный вариант",
            "price": 1899,
            "reviews": 220,
            "link": build_wb_link(base, "4.5", max_price="3000")
        },
        {
            "name": f"⭐ {query.capitalize()} — Высокий рейтинг",
            "price": 3499,
            "reviews": 176,
            "link": build_wb_link(base, "4.9")
        },
        {
            "name": f"📦 {query.capitalize()} — Хит сезона",
            "price": 3999,
            "reviews": 301,
            "link": build_wb_link(base, "4.7", "new")
        }
    ]

# === Команда /start — красивое приветствие ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"step": "start"}

    keyboard = [
        [InlineKeyboardButton("🔍 Начать поиск", callback_data="search")],
        [InlineKeyboardButton("📌 Подписаться на канал", url=CHANNEL_LINK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎉 *Привет! Добро пожаловать в бот по поиску самых выгодных цен на Wildberries!* 🛍️\n\n"
        "🔥 Здесь ты найдёшь:\n"
        "✅ *Топовые товары* с самыми высокими оценками ⭐\n"
        "💰 *Максимальные скидки* и лучшие цены 💸\n"
        "📦 *Проверенные отзывы* от тысяч покупателей 📣\n\n"
        "📌 Подпишись на канал: [*Лучшее с Wildberries | DenShop1*](https://t.me/+uGrNl01GXGI4NjI6)\n"
        "Там — только самые горячие скидки и лайфхаки! 🔥\n\n"
        "🚀 Просто нажми кнопку ниже и начни экономить уже сейчас!",
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

# === Обработчик кнопок ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if query.data == "search":
        await query.edit_message_text(
            "Отлично! 🔥\n"
            "Теперь напиши, что ты хочешь найти на Wildberries.\n\n"
            "Например:\n"
            "• Наушники Sony\n"
            "• Кроссовки\n"
            "• Power Bank"
        )

# === Обработка текстового запроса ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if len(text) < 2:
        await update.message.reply_text("❌ Запрос слишком короткий. Введите хотя бы 2 символа.")
        return

    # Эффект "печатает..."
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)
    time.sleep(1.5)  # Имитация поиска

    # Сообщение с гиперссылкой на канал
    await update.message.reply_text(
        f"🔥 [*Лучшее с Wildberries | DenShop1*](https://t.me/+uGrNl01GXGI4NjI6)\n"
        f"🔍 Ищу: *{text}*",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

    # Получаем топ-5 ссылок
    results = get_top5_links(text)

    if results:
        message = "🏆 *Топ-5 самых выгодных предложений:*\n\n"
        for i, r in enumerate(results, 1):
            stars = "⭐" * min(5, max(1, r['reviews'] // 50))
            message += (
                f"{i}. *{r['name']}*\n"
                f"   💰 {r['price']:,} ₽  |  {r['reviews']} отзывов  {stars}\n"
                f"   🔗 [Перейти]({r['link']})\n\n"
            )
    else:
        message = "❌ Ничего не найдено. Попробуй уточнить запрос."

    await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

# === Запуск бота ===
if __name__ == "__main__":
    keep_alive()  # Запускаем Flask-сервер

    if not TELEGRAM_TOKEN:
        logger.error("❗ Бот не может запуститься: не задан TELEGRAM_TOKEN")
    else:
        logger.info("🤖 Бот запускается...")
        app = Application.builder().token(TELEGRAM_TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("✅ Бот запущен и слушает сообщения...")
        app.run_polling()
