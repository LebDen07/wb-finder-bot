# bot.py
import os
import sys
import requests
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from flask import Flask
from threading import Thread
import logging

# 🔍 Проверка версии Python — поможет в логах
print(f"🐍 Используется Python: {sys.version}")
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменной окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    logger.error("❗ ОШИБКА: Не задан TELEGRAM_TOKEN. Установите переменную окружения в Render.")
    sys.exit(1)  # Завершаем, если токена нет
else:
    logger.info("✅ TELEGRAM_TOKEN загружен")

# === Flask-сервер для keep-alive (чтобы Render не "усыплял" сервис) ===
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "🟢 Бот работает Wildberries Search Bot активен."

def run_flask():
    port = int(os.getenv('PORT', 8080))
    logger.info(f"🚀 Flask запущен на порту {port}")
    app_flask.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def keep_alive():
    logger.info("🔧 Запускаем фоновый Flask-сервер для поддержания активности...")
    t = Thread(target=run_flask, daemon=True)
    t.start()

# === Поиск товаров Wildberries ===
def search_wb(query: str) -> list:
    if not query.strip():
        return []

    url = "https://search.wb.ru/exactmatch/ru/common/v4/search"
    params = {
        "query": query.strip(),
        "resultset": "catalog",
        "limit": 20,
        "page": 1
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.wildberries.ru",
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.warning(f"❌ Wildberries вернул статус: {response.status_code}")
            return []

        data = response.json()
        products = data.get("data", {}).get("products", [])
        results = []

        for p in products[:20]:
            price_u = p.get("salePriceU")
            if not price_u:
                continue

            price = price_u // 100
            reviews = p.get("reviewCount", 0)
            name = p.get("name", "Без названия")
            product_id = p.get("id")
            link = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"

            # Фильтры
            if len(name) > 100 or any(word in name.lower() for word in ["доставка", "самовывоз"]):
                continue

            results.append({
                "name": name[:80] + "..." if len(name) > 80 else name,
                "price": price,
                "reviews": reviews,
                "link": link
            })

        # Сортировка: по отзывам (↓), потом цена (↑)
        results.sort(key=lambda x: (-x["reviews"], x["price"]))
        return results[:5]

    except Exception as e:
        logger.error(f"❌ Ошибка при поиске: {e}")
        return []

# === Обработчики ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔍 Начать поиск", callback_data="start_searching")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎉 *Привет Добро пожаловать в бот по поиску самых выгодных цен на Wildberries!* 🛍️\n\n"
        "🔥 Здесь ты найдёшь:\n"
        "✅ *Топовые товары* с самыми высокими оценками ⭐\n"
        "💰 *Максимальные скидки* и лучшие цены 💸\n"
        "📦 *Проверенные отзывы* от тысяч покупателей 📣\n\n"
        "📌 Подпишись на канал: [*Лучшее с Wildberries | DenShop1*](https://t.me/+uGrNl01GXGI4NjI6)\n"
        "Там — только самые горячие скидки и лайфхаки по покупкам 🔥\n\n"
        "🚀 Просто нажми кнопку ниже и начни экономить уже сейчас!",
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "start_searching":
        await query.edit_message_text(
            "Отлично 🔥\n"
            "Теперь напиши, что ты хочешь найти на Wildberries.\n\n"
            "Например:\n"
            "• Наушники Sony\n"
            "• Кроссовки\n"
            "• Power Bank"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if len(query) < 2:
        await update.message.reply_text("❌ Запрос слишком короткий. Введите хотя бы 2 символа.")
        return

    await update.message.reply_text(
        f"🔥 [*Лучшее с Wildberries | DenShop1*](https://t.me/+uGrNl01GXGI4NjI6)\n"
        f"🔍 Ищу: *{query}*",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

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
        message = (
            "❌ Ничего не найдено. Попробуйте:\n"
            "• Уточнить запрос (например, «кроссовки мужские»)\n"
            "• Написать по-другому («наушники» → «наушники беспроводные»)"
        )

    await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

# === Запуск бота ===
if __name__ == "__main__":
    # Запускаем Flask для keep-alive
    keep_alive()

    # Создаём приложение
    logger.info("🤖 Инициализация Telegram-бота...")
    application = Application.builder().token(TOKEN).build()

    # Хендлеры
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("✅ Бот запущен. Ожидание сообщений...")

    # Запуск polling
    try:
        asyncio.run(application.run_polling())
    except KeyboardInterrupt:
        logger.info("💤 Бот остановлен вручную.")
    except Exception as e:
        logger.critical(f"💥 Критическая ошибка: {e}")
