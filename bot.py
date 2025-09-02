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
    return "✨ Бот для Wildberries работает 24/7"

def run():
    port = int(os.getenv('PORT', 8080))
    app_flask.run(host='0.0.0.0', port=port)

def keep_alive():
    logger.info("🚀 Запускаем Flask-сервер...")
    t = Thread(target=run)
    t.daemon = True
    t.start()

# === Удаление старых сообщений ===
async def delete_previous_messages(context: ContextTypes.DEFAULT_TYPE, chat_id: int, keep_last: int = 2):
    if "message_ids" not in context.user_data:
        return
    message_ids = context.user_data["message_ids"]
    to_delete = message_ids[:-keep_last] if len(message_ids) > keep_last else message_ids
    for msg_id in to_delete:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение {msg_id}: {e}")
    context.user_data["message_ids"] = message_ids[-keep_last:]

# === Сохранение ID сообщений ===
async def save_message_id(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    if "message_ids" not in context.user_data:
        context.user_data["message_ids"] = []
    context.user_data["message_ids"].append(message_id)

# === Команда /start — кинематографическое приветствие ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Удаляем старые сообщения
    await delete_previous_messages(context, chat_id, keep_last=0)

    # Эффект "печатает..."
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    await asyncio.sleep(1.5)

    # Сообщение 1
    msg = await context.bot.send_message(chat_id=chat_id, text="💫")
    await save_message_id(context, chat_id, msg.message_id)
    await asyncio.sleep(0.5)

    # Сообщение 2
    msg = await context.bot.send_message(chat_id=chat_id, text="🛒 Добро пожаловать в...")
    await save_message_id(context, chat_id, msg.message_id)
    await asyncio.sleep(1.0)

    # Сообщение 3 — с ссылкой на канал
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🌟 *единственный Telegram-бот в России, предназначенный для мониторинга и поиска товаров на маркетплейсе WB*\n\n"
            "📌 Подпишитесь на основной канал:\n"
            "[*Лучшее с Wildberries | DenShop1*](https://t.me/+uGrNl01GXGI4NjI6)\n"
            "Там — только горячие скидки и лайфхаки! 🔥"
        ),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    await save_message_id(context, chat_id, msg.message_id)
    await asyncio.sleep(1.8)

    # Кнопка
    keyboard = [
        [InlineKeyboardButton("✨ Начать поиск", callback_data="start_searching")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text="🚀 Готовы начать поиск лучших товаров?",
        reply_markup=reply_markup
    )
    await save_message_id(context, chat_id, msg.message_id)

# === Обработчик кнопки ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id

    # Удаляем старые сообщения
    await delete_previous_messages(context, chat_id, keep_last=0)

    if query.data == "start_searching":
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(1.2)

        msg = await context.bot.send_message(
            chat_id=chat_id,
            text="🔍 *Введите, что вы хотите найти на Wildberries:*",
            parse_mode="Markdown"
        )
        await save_message_id(context, chat_id, msg.message_id)

# === Обработка текстового запроса ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    chat_id = update.effective_chat.id

    if len(query) < 2:
        msg = await update.message.reply_text("❌ Запрос слишком короткий.")
        await save_message_id(context, chat_id, msg.message_id)
        return

    # Удаляем старые сообщения
    await delete_previous_messages(context, chat_id, keep_last=0)

    # Эффект "печатает..."
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    await asyncio.sleep(1.5)

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔍 *Ищу лучшие варианты для:* `{query}`",
        parse_mode="Markdown"
    )
    await save_message_id(context, chat_id, msg.message_id)

    # Ещё эффект
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    await asyncio.sleep(1.8)

    # Кнопки с подсказками
    keyboard = [
        [InlineKeyboardButton("🏆 1. Лидер продаж", callback_data=f"tip|{query}|Сортировка: по популярности")],
        [InlineKeyboardButton("💎 2. Самые дорогие", callback_data=f"tip|{query}|Сортировка: от дорогих")],
        [InlineKeyboardButton("💰 3. Самые дешёвые", callback_data=f"tip|{query}|Сортировка: от дешёвых")],
        [InlineKeyboardButton("⭐ 4. Высокий рейтинг", callback_data=f"tip|{query}|Фильтр: рейтинг 4.9+")],
        [InlineKeyboardButton("🔥 5. Хит сезона", callback_data=f"tip|{query}|Сортировка: по популярности + Россия")],
        [InlineKeyboardButton("🔄 Вернуться к поиску другого товара", callback_data="start_searching")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"🎯 *Как искать «{query}» на Wildberries:*\n\n"
             "Нажмите на вариант — я подскажу, какие фильтры применить вручную.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await save_message_id(context, chat_id, msg.message_id)

# === Обработчик советов ===
async def tip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data  # tip|запрос|совет
    parts = data.split("|", 2)
    if len(parts) != 3:
        return

    search_query, tip = parts[1], parts[2]
    chat_id = query.message.chat_id

    # Удаляем старые сообщения
    await delete_previous_messages(context, chat_id, keep_last=0)

    instruction = (
        f"🔍 *Как найти «{search_query}» на Wildberries:*\n\n"
        f"1. Перейдите на [Wildberries](https://www.wildberries.ru)\n"
        f"2. Введите в поиске: `{search_query}`\n"
        f"3. Примените фильтр: *{tip}*\n"
        f"4. Нажмите «Применить»\n\n"
        f"✅ Теперь вы видите лучшие предложения!"
    )

    # Кнопка "Назад"
    keyboard = [[InlineKeyboardButton("🔙 Назад к выбору", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = await query.edit_message_text(instruction, parse_mode="Markdown", reply_markup=reply_markup)
    await save_message_id(context, chat_id, msg.message_id)

# === Обработчик "Назад" ===
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    # Удаляем старые сообщения
    await delete_previous_messages(context, chat_id, keep_last=0)

    # Извлекаем запрос
    try:
        search_query = query.message.text.split("«")[1].split("»")[0]
    except:
        search_query = "товар"

    # Кнопки
    keyboard = [
        [InlineKeyboardButton("🏆 1. Лидер продаж", callback_data=f"tip|{search_query}|Сортировка: по популярности")],
        [InlineKeyboardButton("💎 2. Самые дорогие", callback_data=f"tip|{search_query}|Сортировка: от дорогих")],
        [InlineKeyboardButton("💰 3. Самые дешёвые", callback_data=f"tip|{search_query}|Сортировка: от дешёвых")],
        [InlineKeyboardButton("⭐ 4. Высокий рейтинг", callback_data=f"tip|{search_query}|Фильтр: рейтинг 4.9+")],
        [InlineKeyboardButton("🔥 5. Хит сезона", callback_data=f"tip|{search_query}|Сортировка: по популярности + Россия")],
        [InlineKeyboardButton("🔄 Вернуться к поиску другого товара", callback_data="start_searching")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = await query.edit_message_text(
        text=f"🎯 *Как искать «{search_query}» на Wildberries:*\n\n"
             "Нажмите на вариант — я подскажу, какие фильтры применить вручную.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await save_message_id(context, chat_id, msg.message_id)

# === Запуск бота ===
if __name__ == "__main__":
    keep_alive()  # Запускаем Flask

    if not TELEGRAM_TOKEN:
        logger.error("❗ Бот не может запуститься: не задан TELEGRAM_TOKEN")
    else:
        logger.info("🤖 Бот запускается...")
        app = Application.builder().token(TELEGRAM_TOKEN).build()

        # Хэндлеры
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler, pattern="^start_searching$"))
        app.add_handler(CallbackQueryHandler(tip_handler, pattern="^tip\\|"))
        app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("✅ Бот запущен и слушает сообщения...")
        app.run_polling()
