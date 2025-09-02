# bot.py
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from flask import Flask
from threading import Thread
import logging
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === Токены ===
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

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✨ Начать поиск", callback_data="start_searching")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "💫 Добро пожаловать в...\n\n"
        "🛒 *единственный Telegram-бот в России, предназначенный для мониторинга и поиска товаров на маркетплейсе WB*\n\n"
        "📌 Подпишитесь на основной канал:\n"
        "[*Лучшее с Wildberries | DenShop1*](https://t.me/+uGrNl01GXGI4NjI6)\n"
        "Там — только горячие скидки и лайфхаки! 🔥",
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

# === Обработчик кнопки ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "start_searching":
        await query.edit_message_text("🔍 Напишите, что вы ищете на Wildberries:")

# === Обработка текста ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if len(query) < 2:
        await update.message.reply_text("❌ Запрос слишком короткий.")
        return

    # Эффект "печатает..."
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)
    await asyncio.sleep(1.5)

    # Кнопки
    keyboard = [
        [InlineKeyboardButton("🏆 1. Лидер продаж", url=f"https://www.wildberries.ru/catalog/0/search.aspx?search={query}&dest=-1257786&sort=popular")],
        [InlineKeyboardButton("💎 2. Самые дорогие", url=f"https://www.wildberries.ru/catalog/0/search.aspx?search={query}&dest=-1257786&sort=pricedown")],
        [InlineKeyboardButton("💰 3. Самые дешёвые", url=f"https://www.wildberries.ru/catalog/0/search.aspx?search={query}&dest=-1257786&sort=priceup")],
        [InlineKeyboardButton("⭐ 4. Высокий рейтинг", url=f"https://www.wildberries.ru/catalog/0/search.aspx?search={query}&dest=-1257786&rating=4.9")],
        [InlineKeyboardButton("🔥 5. Хит сезона", url=f"https://www.wildberries.ru/catalog/0/search.aspx?search={query}&dest=-1257786&sort=popular")],
        [InlineKeyboardButton("🔄 Вернуться к поиску другого товара", callback_data="start_searching")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🎯 *Вот как можно искать «{query}»:*\n\nВыберите вариант:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# === Запуск бота ===
if __name__ == "__main__":
    keep_alive()

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
