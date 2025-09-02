# bot.py
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from flask import Flask
from threading import Thread
import logging
import urllib.parse

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === Токены и настройки ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_LINK = "https://t.me/+uGrNl01GXGI4NjI6"

if not TELEGRAM_TOKEN:
    logger.error("❗ TELEGRAM_TOKEN не задан")
else:
    logger.info("✅ TELEGRAM_TOKEN загружен")

# === Flask для поддержания активности ===
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "✅ Бот работает 24/7"

def run():
    port = int(os.getenv('PORT', 8080))
    app_flask.run(host='0.0.0.0', port=port)

def keep_alive():
    logger.info("🚀 Запускаем Flask-сервер...")
    t = Thread(target=run)
    t.daemon = True
    t.start()

# === Состояние пользователя ===
user_data = {}

# === Генерация ссылок в зависимости от выбора ===
def build_link(query: str, params: dict) -> str:
    base = "https://www.wildberries.ru/catalog/0/search.aspx"
    all_params = {"search": query, **params}
    encoded = urllib.parse.urlencode(all_params)
    return f"{base}?{encoded}"

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {}

    keyboard = [
        [InlineKeyboardButton("🔍 Начать поиск", callback_data="start_searching")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎉 *Привет! Добро пожаловать в бот по поиску самых выгодных цен на Wildberries!* 🛍️\n\n"
        "🔥 Здесь ты найдёшь:\n"
        "✅ *Топовые товары* с самыми высокими оценками ⭐\n"
        "💰 *Максимальные скидки* и лучшие цены 💸\n\n"
        "📌 Подпишись на канал: [*Лучшее с Wildberries | DenShop1*](https://t.me/+uGrNl01GXGI4NjI6)\n"
        "🚀 Просто нажми кнопку ниже и начни экономить уже сейчас!",
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

# === Обработчик кнопки ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "start_searching":
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
    query = update.message.text.strip()

    if len(query) < 2:
        await update.message.reply_text("❌ Запрос слишком короткий.")
        return

    # Эффект "печатает..."
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)
    await asyncio.sleep(1.2)

    # Сохраняем запрос
    user_data[user_id]["query"] = query

    # Кодируем запрос для URL
    encoded_query = urllib.parse.quote(query)

    # Кнопки с разными ссылками
    keyboard = [
        [InlineKeyboardButton("1. Лидер продаж", url=build_link(encoded_query, {"page": "1", "sort": "popular"}))],
        [InlineKeyboardButton("2. Премиум версия", url=build_link(encoded_query, {"page": "1", "sort": "rate", "priceU": "10000;1000000"}))],
        [InlineKeyboardButton("3. Бюджетный вариант", url=build_link(encoded_query, {"page": "1", "priceU": "0;3000"}))],
        [InlineKeyboardButton("4. Высокий рейтинг", url=build_link(encoded_query, {"page": "1", "rating": "4.9"}))],
        [InlineKeyboardButton("5. Хит сезона", url=build_link(encoded_query, {"page": "1", "sort": "popular", "dest": "-1257786"}))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем сообщение с кнопками
    message = (
        f"🔍 *Вы искали:* `{query}`\n\n"
        "Выберите категорию поиска:"
    )

    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

# === Запуск бота ===
if __name__ == "__main__":
    keep_alive()  # Запускаем Flask

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
