# bot.py
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from flask import Flask
from threading import Thread
import logging
import urllib.parse

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Flask для Render
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "🤖 Бот работает 24/7"

def run():
    port = int(os.getenv('PORT', 8080))
    app_flask.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# === ИИ-ядро (упрощённая версия) ===
# (Без внешнего API — просто обрабатываем ключевые слова)
def generate_search_query(user_message: str) -> str:
    # Простая логика (можно заменить на Llama/OpenRouter позже)
    query = user_message.lower()
    keywords = []

    if any(word in query for word in ["наушники", "earbuds", "earphones"]):
        keywords.append("наушники")
    if any(word in query for word in ["беспроводные", "wireless", "bluetooth"]):
        keywords.append("беспроводные")
    if any(word in query for word in ["для бега", "спортивные", "водонепроницаемые", "водозащитные"]):
        keywords.append("водонепроницаемые")
    if any(word in query for word in ["недорогие", "дешёвые", "бюджетные"]):
        keywords.append("до 3000")
    if any(word in query for word in ["с лучшими отзывами", "популярные", "топ"]):
        keywords.append("популярные")

    # Если не определили — просто очистим
    if not keywords:
        keywords = [word for word in query.split() if len(word) > 3]

    return " ".join(keywords) if keywords else "товары"

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔍 Начать диалог", callback_data="start_chat")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Привет! Я — *умный помощник* по поиску товаров на Wildberries.\n\n"
        "Я помогу тебе найти *то, что действительно нужно*.\n\n"
        "Задай мне любой вопрос, например:\n"
        "• *Ищу недорогие наушники для бега*\n"
        "• *Нужны кроссовки для парня до 5000₽*\n\n"
        "Я всё уточню и подберу лучшие варианты!",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Что вы ищете сегодня?")

# === Обработка сообщения ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()
    if len(user_message) < 2:
        await update.message.reply_text("❌ Слишком короткий запрос.")
        return

    # Генерируем поисковой запрос
    search_query = generate_search_query(user_message)
    encoded_query = urllib.parse.quote(search_query)

    # Формируем ссылку с фильтрами
    wb_link = f"https://www.wildberries.ru/catalog/0/search.aspx?search={encoded_query}&sort=popular&rating=4.7"

    # Красивый ответ
    message = (
        "🔍 Я понял, что вы ищете: *{query}*\n\n"
        "🏆 Вот лучшие предложения на Wildberries:\n"
        "✅ Сортировка: по популярности\n"
        "⭐ Рейтинг: от 4.7\n"
        "💬 Много отзывов\n\n"
        "🛒 [Перейти к товарам]({link})"
    ).format(query=search_query, link=wb_link)

    await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=False)

# === Запуск ===
if __name__ == "__main__":
    keep_alive()

    if not TELEGRAM_TOKEN:
        logger.error("❗ Не задан TELEGRAM_TOKEN")
    else:
        logger.info("🤖 Бот запускается...")
        app = Application.builder().token(TELEGRAM_TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("✅ Бот запущен и работает 24/7!")
        app.run_polling()
