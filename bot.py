# bot.py
import os
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from flask import Flask
from threading import Thread
import logging

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Flask-сервер для Render
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "✅ Бот работает 24/7"

def run_flask():
    port = int(os.getenv('PORT', 8080))
    app_flask.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# Поиск через API Wildberries
def search_wb(query: str) -> list:
    url = "https://search.wb.ru/exactmatch/ru/common/v4/search"
    params = {"query": query, "resultset": "catalog", "limit": 20}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        products = data.get("data", {}).get("products", [])
        results = []
        for p in products[:20]:
            price = p.get("salePriceU", 0) // 100
            reviews = p.get("reviewCount", 0)
            name = p.get("name", "Без названия")
            link = f"https://www.wildberries.ru/catalog/{p['id']}/detail.aspx"
            if len(name) > 100 or "доставка" in name.lower():
                continue
            results.append({"name": name, "price": price, "reviews": reviews, "link": link})
        results.sort(key=lambda x: (-x["reviews"], x["price"]))
        return results[:5]
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        return []

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔍 Начать поиск", callback_data="start_searching")]]
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

# Кнопка
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "start_searching":
        await query.edit_message_text("Напиши, что хочешь найти на Wildberries.")

# Обработка запроса
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if len(query) < 2:
        await update.message.reply_text("❌ Запрос слишком короткий.")
        return
    await update.message.reply_text(f"🔍 Ищу: *{query}*", parse_mode="Markdown")
    results = search_wb(query)
    if results:
        message = "🏆 *Топ-5 предложений:*\n\n"
        for i, r in enumerate(results, 1):
            stars = "⭐" * min(5, max(1, r['reviews'] // 50))
            message += f"{i}. *{r['name']}*\n   💰 {r['price']:,} ₽ | {r['reviews']} отзывов {stars}\n   🔗 [Перейти]({r['link']})\n\n"
    else:
        message = "❌ Ничего не найдено."
    await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

# Запуск бота
if __name__ == "__main__":
    if not TOKEN:
        logger.error("❗ Не задан TELEGRAM_TOKEN")
    else:
        keep_alive()  # Запускаем Flask
        logger.info("🤖 Бот запускается...")
        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("✅ Бот запущен и работает 24/7!")
        app.run_polling()