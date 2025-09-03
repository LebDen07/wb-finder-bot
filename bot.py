# bot.py
import os
import asyncio
import csv
import threading
import logging  # ✅ Обязательно импортируем logging
import urllib.parse  # ✅ Для build_wb_link
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from flask import Flask

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === Токен бота ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# 🔥 ЗАМЕНИ НА СВОЙ ID (узнай у @userinfobot)
ADMIN_ID = 954944438

if not TELEGRAM_TOKEN:
    logger.error("❗ TELEGRAM_TOKEN не задан")
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
    logger.info("🚀 Запускаем Flask-сервер...")
    t = Thread(target=run)
    t.daemon = True
    t.start()

# === Состояние и логирование ===
user_ids = set()  # Для рассылки
user_last_request = {}  # Для защиты от спама

# Создаём файл логов, если его нет
if not os.path.exists("search_log.csv"):
    with open("search_log.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "user_id", "username", "query"])

def log_search(user_id, username, query):
    """Логируем запрос пользователя"""
    with open("search_log.csv", "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now(), user_id, username, query])

# === Генерация ссылок без aff_id ===
def build_wb_link(query: str, params: dict) -> str:
    base = "https://www.wildberries.ru/catalog/0/search.aspx"
    all_params = {**params, "search": query}
    encoded = urllib.parse.urlencode(all_params)
    return f"{base}?{encoded}"

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown"
    user_ids.add(user_id)

    # Кнопки
    keyboard = [
        [InlineKeyboardButton("🔍 Начать поиск", callback_data="start_searching")],
        [InlineKeyboardButton("📌 Подписаться на канал", url="https://t.me/+uGrNl01GXGI4NjI6")]
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

# === Обработчик кнопок ===
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
    username = update.effective_user.username or "unknown"
    query = update.message.text.strip()

    # Защита от спама
    now = time.time()
    if user_id in user_last_request and now - user_last_request[user_id] < 5:
        await update.message.reply_text("⏳ Подождите 5 секунд между запросами.")
        return
    user_last_request[user_id] = now

    if len(query) < 2:
        await update.message.reply_text("❌ Запрос слишком короткий.")
        return

    # Эффект "печатает..."
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)
    await asyncio.sleep(1.2)

    # Логируем запрос
    log_search(user_id, username, query)

    # Кодируем запрос
    encoded_query = urllib.parse.quote(query)

    # Кнопки с фильтрами
    keyboard = [
        [InlineKeyboardButton("1. Лидер продаж", url=build_wb_link(encoded_query, {"page": "1", "sort": "popular"}))],
        [InlineKeyboardButton("2. Премиум версия", url=build_wb_link(encoded_query, {"page": "1", "sort": "rate", "priceU": "10000;1000000"}))],
        [InlineKeyboardButton("3. Бюджетный вариант", url=build_wb_link(encoded_query, {"page": "1", "priceU": "0;3000"}))],
        [InlineKeyboardButton("4. Высокий рейтинг", url=build_wb_link(encoded_query, {"page": "1", "rating": "4.9"}))],
        [InlineKeyboardButton("5. Хит сезона", url=build_wb_link(encoded_query, {"page": "1", "sort": "popular", "dest": "-1257786"}))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        f"🔍 *Вы искали:* `{query}`\n\n"
        "Выберите категорию поиска:"
    )
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

# === Команда /stats (только для админа) ===
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещён.")
        return

    try:
        with open("search_log.csv", "r", encoding="utf-8") as f:
            lines = f.readlines()
        count = len(lines) - 1  # минус заголовок
        last_searches = "".join(lines[-5:]) if len(lines) > 1 else "Нет данных"
        await update.message.reply_text(
            f"📊 Статистика:\nВсего поисков: {count}\n\nПоследние 5:\n{last_searches}"
        )
    except FileNotFoundError:
        await update.message.reply_text("📊 Нет данных о поиске.")

# === Команда /broadcast (рассылка) ===
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещён.")
        return

    if not context.args:
        await update.message.reply_text("UsageId: /broadcast Привет! Скидки на наушники!")
        return

    message = " ".join(context.args)
    success = 0
    failed = 0

    for uid in user_ids.copy():
        try:
            await context.bot.send_message(chat_id=uid, text=message)
            success += 1
        except Exception as e:
            logger.warning(f"Failed to send to {uid}: {e}")
            failed += 1
            user_ids.discard(uid)

    await update.message.reply_text(f"📨 Рассылка завершена\n✅ Успешно: {success}\n❌ Ошибок: {failed}")

# === Команда /help ===
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Помощь:\n"
        "/start — начать\n"
        "/help — это сообщение\n"
        "Пишите, что ищете — получайте ссылки!\n\n"
        "📌 Подписаться: [Лучшее с Wildberries](https://t.me/+uGrNl01GXGI4NjI6)",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

# === Команда /donate ===
async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❤️ Спасибо за поддержку!\n"
        "Если хотите помочь развитию бота:\n"
        "Сбер: `2202 2002 1234 5678`\n"
        "или [кофе на QR-код](https://example.com/donate-qr.png)",
        disable_web_page_preview=True
    )

# === Запуск бота ===
if __name__ == "__main__":
    keep_alive()  # Запускаем Flask

    if not TELEGRAM_TOKEN:
        logger.error("❗ Бот не может запуститься: не задан TELEGRAM_TOKEN")
    else:
        logger.info("🤖 Бот запускается...")
        app = Application.builder().token(TELEGRAM_TOKEN).build()

        # Добавляем хендлеры
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(CommandHandler("stats", stats))
        app.add_handler(CommandHandler("broadcast", broadcast))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("donate", donate))

        logger.info("✅ Бот запущен и слушает сообщения...")
        app.run_polling(drop_pending_updates=True)

