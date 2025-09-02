# bot.py
import os
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
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

# === Токены из переменных окружения ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # Для ИИ

if not TELEGRAM_TOKEN:
    logger.error("❗ Не задан TELEGRAM_TOKEN")
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

# === Категории для кнопок ===
CATEGORIES = {
    "🎧 Наушники": "наушники",
    "👟 Кроссовки": "кроссовки",
    "📱 Смартфоны": "смартфон",
    "⌚ Часы": "часы",
    "🎒 Рюкзаки": "рюкзак"
}

BUDGETS = ["до 1000₽", "до 3000₽", "до 5000₽", "до 10000₽"]
RATINGS = ["от 4.5", "от 4.7", "от 4.8"]

# === Пример товаров (mock) — можно заменить на API позже ===
MOCK_PRODUCTS = [
    {
        "title": "Наушники беспроводные Sony WF-C500",
        "price": "4 999 ₽",
        "rating": "4.8",
        "reviews": "247",
        "image": "https://cf1.wbstatic.net/big/new/12345678/1.jpg",
        "url": "https://www.wildberries.ru/catalog/12345678/detail.aspx"
    },
    {
        "title": "Кроссовки мужские Nike Air Zoom Pegasus",
        "price": "7 499 ₽",
        "rating": "4.9",
        "reviews": "189",
        "image": "https://cf1.wbstatic.net/big/new/87654321/1.jpg",
        "url": "https://www.wildberries.ru/catalog/87654321/detail.aspx"
    },
    {
        "title": "Смартфон Xiaomi Redmi Note 13 Pro",
        "price": "12 999 ₽",
        "rating": "4.7",
        "reviews": "312",
        "image": "https://cf1.wbstatic.net/big/new/24681357/1.jpg",
        "url": "https://www.wildberries.ru/catalog/24681357/detail.aspx"
    }
]

# === Диалоговое состояние пользователя ===
user_state = {}

# === Запрос к ИИ через OpenRouter ===
def ai_query(prompt: str) -> dict:
    if not OPENROUTER_API_KEY:
        return {"query": prompt, "budget": "до 5000₽", "rating": "4.7"}
    
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
                    {"role": "system", "content": "Ты — ассистент по поиску товаров на Wildberries. Извлеки: что ищет, бюджет, рейтинг. Верни JSON: {query, budget, rating}"},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=15
        )
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        # Простой парсинг JSON (в реальности можно использовать json.loads)
        return eval(content) if "query" in content else {"query": prompt, "budget": "до 5000₽", "rating": "4.7"}
    except Exception as e:
        logger.error(f"❌ Ошибка ИИ: {e}")
        return {"query": prompt, "budget": "до 5000₽", "rating": "4.7"}

# === Генерация ссылки на Wildberries ===
def make_wb_link(query: str, rating: str = "4.7") -> str:
    encoded_query = urllib.parse.quote(query)
    min_rating = rating.replace("от ", "")
    return f"https://www.wildberries.ru/catalog/0/search.aspx?search={encoded_query}&sort=popular&rating={min_rating}"

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = {"step": "start"}

    keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat_{key}")] for key, cat in CATEGORIES.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🛒 *Добро пожаловать в бот по поиску товаров на Wildberries!*\n\n"
        "Выберите категорию или напишите, что ищете:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# === Обработчик кнопок ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data

    if data.startswith("cat_"):
        search_query = data.replace("cat_", "")
        user_state[user_id]["query"] = search_query
        user_state[user_id]["step"] = "budget"

        keyboard = [[InlineKeyboardButton(budg, callback_data=f"budg_{budg}")] for budg in BUDGETS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Вы ищете: *{search_query}*\n\nУкажите бюджет:", reply_markup=reply_markup, parse_mode="Markdown")

    elif data.startswith("budg_"):
        budget = data.replace("budg_", "")
        user_state[user_id]["budget"] = budget
        user_state[user_id]["step"] = "rating"

        keyboard = [[InlineKeyboardButton(rat, callback_data=f"rat_{rat}")] for rat in RATINGS]
        keyboard.append([InlineKeyboardButton("Пропустить", callback_data="rat_от 4.5")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Укажите минимальный рейтинг:", reply_markup=reply_markup, parse_mode="Markdown")

    elif data.startswith("rat_"):
        rating = data.replace("rat_", "")
        user_state[user_id]["rating"] = rating
        final_query = user_state[user_id]["query"]
        full_query = f"{final_query} {user_state[user_id]['budget']}".strip()

        # Генерируем ссылку
        wb_link = make_wb_link(full_query, rating)

        # Показываем "Ищу..."
        await query.edit_message_text("🔍 *Ищу лучшие варианты...*", parse_mode="Markdown")

        # Показываем mock-товары
        for product in MOCK_PRODUCTS:
            if final_query.lower() in product["title"].lower():
                caption = (
                    f"🛍️ *{product['title']}*\n"
                    f"💰 Цена: *{product['price']}*\n"
                    f"⭐ Рейтинг: *{product['rating']}* ({product['reviews']} отзывов)\n\n"
                    f"[🛒 Перейти к товару]({product['url']})"
                )
                try:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=product["image"],
                        caption=caption,
                        parse_mode="Markdown",
                        disable_web_page_preview=True
                    )
                except:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=caption,
                        parse_mode="Markdown",
                        disable_web_page_preview=True
                    )

        # Кнопка "Посмотреть все"
        keyboard = [[InlineKeyboardButton("🌐 Посмотреть все на Wildberries", url=wb_link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ Вот лучшие предложения. Хотите увидеть больше?",
            reply_markup=reply_markup
        )

# === Обработка текстового запроса (через ИИ) ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if len(text) < 2:
        await update.message.reply_text("❌ Запрос слишком короткий.")
        return

    # Отправляем в ИИ
    ai_result = ai_query(text)
    query = ai_result.get("query", text)
    budget = ai_result.get("budget", "до 5000₽")
    rating = ai_result.get("rating", "4.7")

    full_query = f"{query} {budget}"
    wb_link = make_wb_link(query, rating)

    await update.message.reply_text(
        f"🔍 *Ищу:* `{full_query}`\n"
        f"⭐ *Минимальный рейтинг:* `{rating}`",
        parse_mode="Markdown"
    )

    # Показываем mock-товары
    for product in MOCK_PRODUCTS:
        if query.lower() in product["title"].lower():
            caption = (
                f"🛍️ *{product['title']}*\n"
                f"💰 Цена: *{product['price']}*\n"
                f"⭐ Рейтинг: *{product['rating']}* ({product['reviews']} отзывов)\n\n"
                f"[🛒 Перейти к товару]({product['url']})"
            )
            try:
                await context.bot.send_photo(
                    chat_id=update.message.chat_id,
                    photo=product["image"],
                    caption=caption,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
            except:
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=caption,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )

    # Кнопка
    keyboard = [[InlineKeyboardButton("🌐 Посмотреть все на Wildberries", url=wb_link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=update.message.chat_id,
        text="✅ Вот лучшие предложения!",
        reply_markup=reply_markup
    )

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
