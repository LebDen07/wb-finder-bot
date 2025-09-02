# bot.py
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from flask import Flask
from threading import Thread
import logging
import urllib.parse
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

# === Команда /start — новое приветствие ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Эффект "печатает..."
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    await asyncio.sleep(1.2)

    # Сообщение 1
    await context.bot.send_message(
        chat_id=chat_id,
        text="💫 Добро пожаловать в...",
        parse_mode="Markdown"
    )
    await asyncio.sleep(0.8)

    # Сообщение 2 — с ссылкой на канал
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🛒 *единственный Telegram-бот в России, предназначенный для мониторинга и поиска товаров на маркетплейсе WB*\n\n"
            "📌 Подпишитесь на основной канал:\n"
            "[*Лучшее с Wildberries | DenShop1*](https://t.me/+uGrNl01GXGI4NjI6)\n"
            "Там — только горячие скидки и лайфхаки! 🔥"
        ),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    await asyncio.sleep(1.0)

    # Кнопка
    keyboard = [
        [InlineKeyboardButton("✨ Начать поиск", callback_data="start_searching")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=chat_id,
        text="🚀 Готовы начать поиск лучших товаров?",
        reply_markup=reply_markup
    )

# === Обработчик кнопки ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "start_searching":
        await query.edit_message_text(
            "Отлично! 🔥\n"
            "Теперь напишите, что вы хотите найти на Wildberries.\n\n"
            "Например:\n"
            "• Наушники Sony\n"
            "• Кроссовки\n"
            "• Power Bank"
        )

# === Обработка текстового запроса ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if len(query) < 2:
        await update.message.reply_text("❌ Запрос слишком короткий.")
        return

    chat_id = update.effective_chat.id

    # Эффект "печатает..."
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    await asyncio.sleep(1.5)

    # Показываем, что ищем
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔍 *Ищу лучшие варианты для:* `{query}`",
        parse_mode="Markdown"
    )

    # Ещё эффект
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    await asyncio.sleep(1.8)

    # Кнопки с подсказками (не ссылки, а советы по фильтрам)
    keyboard = [
        [
            InlineKeyboardButton(
                "🏆 1. Лидер продаж",
                callback_data=f"tip|{query}|Сортировка: по популярности"
            )
        ],
        [
            InlineKeyboardButton(
                "💎 2. Самые дорогие",
                callback_data=f"tip|{query}|Сортировка: от дорогих"
            )
        ],
        [
            InlineKeyboardButton(
                "💰 3. Самые дешёвые",
                callback_data=f"tip|{query}|Сортировка: от дешёвых"
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ 4. Высокий рейтинг",
                callback_data=f"tip|{query}|Фильтр: рейтинг 4.9+"
            )
        ],
        [
            InlineKeyboardButton(
                "🔥 5. Хит сезона",
                callback_data=f"tip|{query}|Сортировка: по популярности + Россия"
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 Вернуться к поиску другого товара",
                callback_data="start_searching"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        f"🎯 *Как искать «{query}» на Wildberries:*\n\n"
        "Нажмите на вариант — я подскажу, какие фильтры применить вручную."
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# === Обработчик советов ===
async def tip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data  # tip|запрос|совет
    parts = data.split("|", 2)
    if len(parts) != 3:
        return

    search_query, tip = parts[1], parts[2]

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

    await query.edit_message_text(instruction, parse_mode="Markdown", reply_markup=reply_markup)

# === Обработчик "Назад" ===
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Просто повторяем меню
    search_query = query.message.text.split("«")[1].split("»")[0]  # извлекаем запрос

    keyboard = [
        [InlineKeyboardButton("🏆 1. Лидер продаж", callback_data=f"tip|{search_query}|Сортировка: по популярности")],
        [InlineKeyboardButton("💎 2. Самые дорогие", callback_data=f"tip|{search_query}|Сортировка: от дорогих")],
        [InlineKeyboardButton("💰 3. Самые дешёвые", callback_data=f"tip|{search_query}|Сортировка: от дешёвых")],
        [InlineKeyboardButton("⭐ 4. Высокий рейтинг", callback_data=f"tip|{search_query}|Фильтр: рейтинг 4.9+")],
        [InlineKeyboardButton("🔥 5. Хит сезона", callback_data=f"tip|{search_query}|Сортировка: по популярности + Россия")],
        [InlineKeyboardButton("🔄 Вернуться к поиску другого товара", callback_data="start_searching")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        f"🎯 *Как искать «{search_query}» на Wildberries:*\n\n"
        "Нажмите на вариант — я подскажу, какие фильтры применить вручную."
    )

    await query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)

# === Запуск бота ===
if __name__ == "__main__":
    keep_alive()  # Запускаем Flask

    if not TELEGRAM_TOKEN:
        logger.error("❗ Бот не может запуститься: не задан TELEGRAM_TOKEN")
    else:
        logger.info("🤖 Бот запускается...")
        app = Application.builder().token(TELEGRAM_TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler, pattern="^start_searching$"))
        app.add_handler(CallbackQueryHandler(tip_handler, pattern="^tip\\|"))
        app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("✅ Бот запущен и слушает сообщения...")
        app.run_polling()
