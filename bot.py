# bot.py
import os
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from flask import Flask
from threading import Thread
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменной окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Проверяем, задан ли токен
if not TOKEN:
    logger.error("❗ Не задан TELEGRAM_TOKEN. Установите переменную окружения.")
else:
    logger.info("✅ TELEGRAM_TOKEN загружен")

# === Flask-сервер для поддержания активности (keep_alive) ===
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
    t.daemon = True  # поток завершится при остановке основного
    t.start()

# === Поиск товаров через API Wildberries ===
def search_wb(query: str) -> list:
    url = "https://search.wb.ru/exactmatch/ru/common/v4/search"
    params = {
        "query": query,
        "resultset": "catalog",
        "limit": 20,
        "page": 1
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.warning(f"❌ Ошибка API Wildberries: {response.status_code}")
            return []

        data = response.json()
        products = data.get("data", {}).get("products", [])
        results = []

        for p in products[:20]:
            price_u = p.get("salePriceU")
            if not price_u:
                continue
            price = price_u // 100  # в рублях
            reviews = p.get("reviewCount", 0)
            name = p.get("name", "Без названия")
            product_id = p.get("id")
            link = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"

            # Фильтры
            if len(name) > 100 or "доставка" in name.lower():
                continue

            results.append({
                "name": name,
                "price": price,
                "reviews": reviews,
                "link": link
            })

        # Сортировка: по отзывам (↓), затем цена (↑)
        results.sort(key=lambda x: (-x["reviews"], x["price"]))
        return results[:5]

    except Exception as e:
        logger.error(f"❌ Ошибка при поиске: {e}")
        return []

# === Обработчики команд ===

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔍 Начать поиск", callback_data="start_searching")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
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

# Обработчик кнопки
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

# Обработка текстового запроса
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if len(query) < 2:
        await update.message.reply_text("❌ Запрос слишком короткий. Введите хотя бы 2 символа.")
        return

    # Показываем, что ищем
    await update.message.reply_text(
        f"🔥 [*Лучшее с Wildberries | DenShop1*](https://t.me/+uGrNl01GXGI4NjI6)\n"
        f"🔍 Ищу: *{query}*",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

    # Ищем товары
    results = search_wb(query)

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

# === Запуск бота ===
if __name__ == "__main__":
    # Запускаем Flask-сервер (чтобы Render считал сервис живым)
    keep_alive()

    if not TOKEN:
        logger.error("❗ Бот не может запуститься: не задан TELEGRAM_TOKEN")
    else:
        logger.info("🤖 Инициализация бота...")
        app = Application.builder().token(TOKEN).build()

        # Добавляем хендлеры
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("✅ Бот запущен и слушает сообщения...")
        app.run_polling()
