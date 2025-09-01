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
import urllib.parse

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print(f"🐍 Python: {sys.version}")

# Токен
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    logger.error("❗ TELEGRAM_TOKEN не задан")
    sys.exit(1)

# === Flask для keep-alive ===
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "🟢 Бот работает"

def run_flask():
    port = int(os.getenv('PORT', 10000))
    app_flask.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()

# === Поиск ТОП-товаров по запросу (как на tags/obuvi) ===
def search_wb(query: str) -> list:
    if not query.strip():
        return []

    # Кодируем запрос
    keyword = urllib.parse.quote(query.strip())

    # 🔥 Рабочий эндпоинт 2025 — используется в подсказках WB
    url = f"https://catalog.wb.ru/catalog/autosearch/data"

    params = {
        "query": query.strip(),
        "dest": -1257786,  # Россия
        "lang": "ru",
        "curr": "rub",
        "limit": 100,
        "page": 1
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.wildberries.ru/",
        "Origin": "https://www.wildberries.ru",
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        logger.info(f"🔍 Запрос к: {url}?query={query}")
        response = requests.get(url, params=params, headers=headers, timeout=10)

        logger.info(f"📊 Статус: {response.status_code}")

        if response.status_code != 200:
            return []

        data = response.json()
        products = data.get("data", {}).get("products", [])

        if not products:
            logger.warning("📦 Ничего не найдено по запросу")
            return []

        results = []
        seen_ids = set()  # Убираем дубли

        for p in products:
            product_id = p.get("id")
            if not product_id or product_id in seen_ids:
                continue
            seen_ids.add(product_id)

            price_u = p.get("priceU") or p.get("salePriceU")
            if not price_u:
                continue

            price = price_u // 100
            reviews = p.get("feedbacks", 0)
            name = p.get("name", "Без названия")
            brand = p.get("brand", "").strip()
            full_name = f"{brand} {name}".strip()
            link = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"

            # Фильтрация
            if len(full_name) > 100 or any(word in full_name.lower() for word in ["доставка", "самовывоз"]):
                continue

            results.append({
                "name": full_name[:80] + "..." if len(full_name) > 80 else full_name,
                "price": price,
                "reviews": reviews,
                "link": link
            })

        # Сортировка: по популярности (отзывам) → цена
        results.sort(key=lambda x: (-x["reviews"], x["price"]))
        return results[:5]  # ТОП-5

    except Exception as e:
        logger.error(f"❌ Ошибка при поиске: {e}")
        return []

# === Обработчики ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardButton("🔍 Начать поиск", callback_data="start_searching")
    reply_markup = InlineKeyboardMarkup([keyboard])

    await update.message.reply_text(
        "🎉 *Привет Добро пожаловать в бот по поиску самых выгодных цен на Wildberries!* 🛍️\n\n"
        "🔥 Здесь ты найдёшь:\n"
        "✅ *Топовые товары* с самыми высокими оценками ⭐\n"
        "💰 *Максимальные скидки* и лучшие цены 💸\n"
        "📦 *Проверенные отзывы* от тысяч покупателей 📣\n\n"
        "📌 Подпишись на канал: *Лучшее с Wildberries | DenShop1*(https://t.me/+uGrNl01GXGI4NjI6)\n"
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

    # Показываем, что ищем
    await update.message.reply_text(
        f"🔥 *Лучшее с Wildberries | DenShop1*(https://t.me/+uGrNl01GXGI4NjI6)\n"
        f"🔍 Ищу *ТОПовые товары* по запросу: *{query}*",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

    # Ищем
    results = search_wb(query)

    if results:
        message = "🏆 *ТОП-5 самых популярных товаров по версии Wildberries:*\n\n"
        for i, r in enumerate(results, 1):
            stars = "⭐" * min(5, max(1, r['reviews'] // 50))
            message += (
                f"{i}. *{r['name']}*\n"
                f" 💰 {r['price']:,} ₽ | {r['reviews']} отзывов {stars}\n"
                f" 🔗 Перейти({r['link']})\n\n"
            )
    else:
        message = (
            "❌ Ничего не найдено. Попробуй:\n"
            "• Уточнить запрос (например, «кроссовки мужские»)\n"
            "• Написать по-другому («наушники» → «наушники беспроводные»)\n"
            "• Попробовать позже — иногда WB временно блокирует запросы"
        )

    await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

# === Запуск бота ===
if __name__ == "__main__":
    keep_alive()

    logger.info("🤖 Инициализация бота...")
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("✅ Бот запущен. Ожидание сообщений...")

    try:
        asyncio.run(application.run_polling())
    except KeyboardInterrupt:
        logger.info("💤 Бот остановлен вручную.")
    except Exception as e:
        logger.critical(f"💥 Критическая ошибка: {e}")
