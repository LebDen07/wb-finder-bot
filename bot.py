# wb_finder_bot_lite.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from flask import Flask
from threading import Thread
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ⚙️ Настройки
TELEGRAM_TOKEN = "8359908342:AAFT5jgAHvDo5wnuZqZEM1A4OkboU4TE4IU"  # 🔥 Заменить в Render через переменные
CHANNEL_LINK = "https://t.me/+uGrNl01GXGI4NjI6"
SEARCH_BASE = "https://www.wildberries.ru/catalog/0/search.aspx?search="

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

# 🧠 Пример "умного" поиска: возвращает топ-5 ссылок по запросу
def search_wb_links(query: str) -> list:
    # Примеры товаров (можно заменить на API или БД позже)
    base_query = query.replace(" ", "+")
    return [
        {
            "name": f"Топ 1: {query} — лучший выбор",
            "price": 2999,
            "reviews": 150,
            "link": f"{SEARCH_BASE}{base_query}&xsubject=100"
        },
        {
            "name": f"Топ 2: {query} — премиум версия",
            "price": 4599,
            "reviews": 98,
            "link": f"{SEARCH_BASE}{base_query}&xsubject=200"
        },
        {
            "name": f"Топ 3: {query} — бюджетный вариант",
            "price": 1899,
            "reviews": 220,
            "link": f"{SEARCH_BASE}{base_query}&xsubject=300"
        },
        {
            "name": f"Топ 4: {query} — с гарантией",
            "price": 3499,
            "reviews": 176,
            "link": f"{SEARCH_BASE}{base_query}&xsubject=400"
        },
        {
            "name": f"Топ 5: {query} — хит продаж",
            "price": 3999,
            "reviews": 301,
            "link": f"{SEARCH_BASE}{base_query}&xsubject=500"
        }
    ]

# 🤖 Команда /start с анимацией, ссылкой и кнопкой
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Кнопка
    keyboard = [[InlineKeyboardButton("🔍 Начать поиск", callback_data="start_searching")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Текст с гиперссылкой на канал
    await update.message.reply_text(
        "🎉 *Привет! Добро пожаловать в бот по поиску самых выгодных цен на Wildberries!* 🛍️\n\n"
        "🔥 Здесь ты найдёшь:\n"
        "✅ *Топовые товары* с самыми высокими оценками ⭐\n"
        "💰 *Максимальные скидки* и лучшие цены 💸\n"
        "📦 *Проверенные отзывы* от тысяч покупателей 📣\n\n"
        "📌 Подпишись на канал: [*Лучшее с Wildberries | DenShop1*](https://t.me/+uGrNl01GXGI4NjI6)\n"
        "Там — только самые горячие скидки и лайфхаки по покупкам! 🔥\n\n"
        "🚀 Просто нажми кнопку ниже и начни экономить уже сейчас!",
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

# 🤖 Обработчик кнопки
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

# 🤖 Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if len(query) < 2:
        await update.message.reply_text("❌ Запрос слишком короткий.")
        return

    # Сообщение с гиперссылкой на канал
    await update.message.reply_text(
        f"🔥 [*Лучшее с Wildberries | DenShop1*](https://t.me/+uGrNl01GXGI4NjI6)\n"
        f"Ищу: *{query}*",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

    results = search_wb_links(query)

    if results:
        message = "🏆 *Топ-5 самых выгодных предложений:*\n\n"
        for i, r in enumerate(results, 1):
            stars = "⭐" * min(5, max(1, r['reviews'] // 50))
            message += (
                f"{i}. *{r['name']}*\n"
                f"   💰 {r['price']:,.0f} ₽  |  {r['reviews']} отзывов  {stars}\n"
                f"   🔗 [Перейти]({r['link']})\n\n"
            )
    else:
        message = "❌ Ничего не найдено. Попробуй уточнить запрос."

    await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

# 🚀 Запуск бота
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
