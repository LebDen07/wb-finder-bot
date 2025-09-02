# bot.py
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from flask import Flask
from threading import Thread
import logging
import urllib.parse

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токены
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Flask для Render
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "🤖 Умный бот для Wildberries работает 24/7"

def run():
    port = int(os.getenv('PORT', 8080))
    app_flask.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# === Запрос к ИИ через OpenRouter ===
def ai_query(prompt: str, history: str = "") -> str:
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "qwen/qwen2.5-7b-instruct",  # можно заменить на llama-3.1-8b-instant
                "messages": [
                    {"role": "system", "content": "Ты — умный помощник по поиску товаров на Wildberries. Задавай уточняющие вопросы, чтобы понять, что нужно пользователю. В конце сформулируй краткий поисковой запрос на русском. Не предлагай ссылки, просто сформулируй запрос."},  # noqa: E501
                    {"role": "user", "content": history + "\n\n" + prompt}
                ]
            },
            timeout=15
        )
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"❌ Ошибка ИИ: {e}")
        return "Не удалось сформировать запрос. Попробуйте: наушники, кроссовки и т.д."

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["history"] = ""
    keyboard = [[InlineKeyboardButton("🔍 Начать диалог", callback_data="start_chat")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Привет! Я — *умный помощник* по поиску товаров на Wildberries.\n\n"
        "Я задам несколько вопросов, чтобы точнее найти то, что тебе нужно.\n\n"
        "Задай мне любой вопрос, например:\n"
        "• *Ищу недорогие наушники для бега*\n"
        "• *Нужны кроссовки для парня до 5000₽*",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Что вы ищете сегодня?")

# === Обработка сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()
    history = context.user_data.get("history", "")

    # Отправляем в ИИ
    ai_response = ai_query(user_message, history)

    # Если ИИ вернул запрос — генерируем ссылку
    if any(word in ai_response.lower() for word in ["наушники", "кроссовки", "смартфон", "ищу", "найди", "подбери"]):
        # Чистим ответ
        search_query = "".join(c for c in ai_response if c.isalnum() or c in " -.")
        search_query = search_query.replace("Ищу ", "").replace("Найди ", "").strip()

        # Кодируем для URL
        encoded_query = urllib.parse.quote(search_query)

        # Генерируем ссылку с фильтрами
        wb_link = f"https://www.wildberries.ru/catalog/0/search.aspx?search={encoded_query}&sort=popular&rating=4.7"

        message = (
            "🔍 Я понял, что вы ищете: *{query}*\n\n"
            "🏆 Вот лучшие предложения на Wildberries:\n"
            "✅ Сортировка: по популярности\n"
            "⭐ Рейтинг: от 4.7\n"
            "💬 Много отзывов\n\n"
            "🛒 [Перейти к товарам]({link})"
        ).format(query=search_query, link=wb_link)
    else:
        message = ai_response
        # Добавляем в историю
        context.user_data["history"] += f"\nПользователь: {user_message}\nАссистент: {ai_response}"

    await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=False)

# === Запуск бота ===
if __name__ == "__main__":
    keep_alive()

    if not TELEGRAM_TOKEN:
        logger.error("❗ Не задан TELEGRAM_TOKEN")
    elif not OPENROUTER_API_KEY:
        logger.error("❗ Не задан OPENROUTER_API_KEY")
    else:
        logger.info("🤖 Бот запускается...")
        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("✅ Бот запущен и работает 24/7!")
        app.run_polling()
