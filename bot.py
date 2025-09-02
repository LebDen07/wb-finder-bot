# bot.py
import os
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ChatAction
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
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # Для ИИ (опционально)

CHANNEL_LINK = "https://t.me/+uGrNl01GXGI4NjI6"
SEARCH_BASE = "https://www.wildberries.ru/catalog/0/search.aspx?"

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

# === Пример "умного" поиска с фильтрами ===
def build_wb_link(query: str, rating: str = "4.7", sort: str = "popular", max_price: str = None) -> str:
    params = {
        "search": query,
        "sort": sort,
        "rating": rating.replace("от ", "")
    }
    if max_price:
        params["price"] = f"0;{max_price}"
    encoded = urllib.parse.urlencode(params)
    return f"https://www.wildberries.ru/catalog/0/search.aspx?{encoded}"

# === Генерация топ-5 ссылок (можно заменить на API) ===
def get_top5_links(query: str) -> list:
    base = query.replace(" ", "+")
    return [
        {"name": f"🔥 {query.capitalize()} — Лидер продаж", "price": 2999, "reviews": 150, "link": build_wb_link(base, "4.7")},
        {"name": f"💎 {query.capitalize()} — Премиум", "price": 4599, "reviews": 98, "link": build_wb_link(base, "4.8")},
        {"name": f"💰 {query.capitalize()} — Бюджет", "price": 1899, "reviews": 220, "link": build_wb_link(base, "4.5", max_price="3000")},
        {"name": f"⭐ {query.capitalize()} — С высоким рейтингом", "price": 3499, "reviews": 176, "link": build_wb_link(base, "4.9")},
        {"name": f"📦 {query.capitalize()} — Хит сезона", "price": 3999, "reviews": 301, "link": build_wb_link(base, "4.7", "new")}
    ]

# === ИИ-анализ запроса (через OpenRouter) ===
def ai_understand(text: str) -> dict:
    if not OPENROUTER_API_KEY:
        return {"intent": "search", "query": text, "budget": None, "rating": "4.7"}

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "qwen/qwen2.5-7b-instruct",
                "messages": [
                    {"role": "system", "content": "Определи: что ищет, бюджет, рейтинг. Верни JSON: {query, budget, rating}"},
                    {"role": "user", "content": text}
                ]
            },
            timeout=10
        )
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        import json
        return json.loads(content.replace("'", '"'))
    except Exception as e:
        logger.error(f"❌ ИИ ошибка: {e}")
        return {"query": text, "budget": None, "rating": "4.7"}

# === /start — красивое приветствие ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"step": "start"}

    keyboard = [
        [InlineKeyboardButton("🔍 Найти товар", callback_data="search")],
        [InlineKeyboardButton("📌 Подписаться", url=CHANNEL_LINK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎉 *Привет! Я — ваш личный ассистент по поиску на Wildberries!* 🛍️\n\n"
        "Я помогу найти:\n"
        "✅ *Топовые товары* с высоким рейтингом ⭐\n"
        "💰 *Лучшие цены* и скидки 💸\n"
        "📦 *Проверенные отзывы* от реальных покупателей 📣\n\n"
        "📌 *Подпишитесь на канал:* [*Лучшее с Wildberries | DenShop1*](https://t.me/+uGrNl01GXGI4NjI6)\n"
        "Там — только горячие скидки и лайфхаки! 🔥\n\n"
        "Выберите действие:",
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
        await query.edit_message_text("Что вы ищете? Напишите, например: *наушники*, *кроссовки*, *power bank*", parse_mode="Markdown")

# === Обработка текстового запроса ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if len(text) < 2:
        await update.message.reply_text("❌ Запрос слишком короткий. Введите хотя бы 2 символа.")
        return

    # "печатает..."
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)
    time.sleep(1.5)

    # Показываем, что ищем
    await update.message.reply_text(
        f"🔍 *Ищу лучшие варианты для:* `{text}`\n"
        f"⭐ *Минимальный рейтинг:* `4.7`",
        parse_mode="Markdown"
    )

    # Анализируем через ИИ
    ai_result = ai_understand(text)
    search_query = ai_result.get("query", text)

    # Получаем топ-5
    results = get_top5_links(search_query)

    # Отправляем карточки
    for i, r in enumerate(results, 1):
        stars = "⭐" * min(5, max(1, r['reviews'] // 50))
        message = (
            f"{i}. *{r['name']}*\n"
            f"   💰 {r['price']:,} ₽  |  {r['reviews']} отзывов  {stars}\n"
            f"   🔗 [Перейти]({r['link']})"
        )
        await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=message,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    # Кнопка "Ещё"
    keyboard = [[InlineKeyboardButton("🔄 Искать снова", callback_data="search")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=update.message.chat_id,
        text="✅ Готово! Хотите найти что-то ещё?",
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
