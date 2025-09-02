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

# === Получаем токены из переменных окружения ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Проверка токенов
if not TELEGRAM_TOKEN:
    logger.error("❗ TELEGRAM_TOKEN не задан. Установите в переменных окружения Render.")
else:
    logger.info("✅ TELEGRAM_TOKEN загружен")

if not OPENROUTER_API_KEY:
    logger.error("❗ OPENROUTER_API_KEY не задан. Получите на https://openrouter.ai/keys")
else:
    logger.info("✅ OPENROUTER_API_KEY загружен")

# === Flask-сервер для поддержания активности ===
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
                "model": "qwen/qwen2.5-7b-instruct",
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
        return "Не удалось сформировать запрос. Попробуйте уточнить: наушники, кроссовки и т.д."

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сбрасываем историю диалога
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

# === Обработчик кнопки ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Что вы ищете сегодня?")

# === Обработка текстового запроса ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()
    if len(user_message) < 2:
        await update.message.reply_text("❌ Запрос слишком короткий. Введите хотя бы 2 символа.")
        return

    # Получаем историю диалога
    history = context.user_data.get("history", "")

    # Отправляем в ИИ
    ai_response = ai_query(user_message, history)

    # Если ИИ вернул похожий на запрос текст — считаем, что это искомый запрос
    if any(kw in ai_response.lower() for kw in ["наушники", "кроссовки", "смартфон", "ищу", "найди", "подбери", "покажи", "рекомендуй"]):
        # Чистим ответ
        search_query = "".join(c for c in ai_response if c.isalnum() or c in " -.")
        search_query = search_query.replace("Ищу ", "").replace("Найди ", "").replace("Подбери ", "").strip()
        if len(search_query) < 2:
            search_query = user_message  # резерв

        # Кодируем для URL
        encoded_query = urllib.parse.quote(search_query)

        # Генерируем ссылку с фильтрами: популярность, рейтинг ≥ 4.7
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
    keep_alive()  # Запускаем Flask-сервер

    # Проверяем, заданы ли токены
    if not TELEGRAM_TOKEN:
        logger.error("❗ Бот не может запуститься: не задан TELEGRAM_TOKEN")
    elif not OPENROUTER_API_KEY:
        logger.error("❗ Бот не может запуститься: не задан OPENROUTER_API_KEY")
    else:
        logger.info("🤖 Бот запускается...")
        app = Application.builder().token(TELEGRAM_TOKEN).build()

        # Добавляем хендлеры
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("✅ Бот запущен и слушает сообщения...")
        app.run_polling()
