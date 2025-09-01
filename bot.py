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

# === Поиск товаров — через прокси (гарантированно работает) ===
def search_wb(query: str) -> list:
    if not query.strip():
        return []

    logger.info(f"🔍 Поиск через прокси: '{query}'")
    encoded_query = urllib.parse.quote(query.strip())
    proxy_url = f"https://wbproxy.vercel.app/api/search?q={encoded_query}"

    try:
        response = requests.get(proxy_url, timeout=15)
        logger.info(f"📊 Статус прокси: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"❌ Ошибка прокси: {response.status_code}")
            return None  # Ошибка сети — фолбэк

        data = response.json()

        if not data.get("products"):
            logger.warning("📦 Нет товаров в ответе прокси")
            return []

        products = data["products"]
        result = []
        seen_ids = set()

        for p in products[:50]:
            pid = p.get("id")
            if not pid or pid in seen_ids:
                continue
            seen_ids.add(pid)

            price = p.get("price", 0)
            if price == 0:
                continue

            reviews = p.get("reviews", 0)
            name = p.get("name", "Без названия")
            brand = p.get("brand", "").strip()
            full_name = f"{brand} {name}".strip()[:80]
            link = f"https://www.wildberries.ru/catalog/{pid}/detail.aspx"

            result.append({
                "name": full_name,
                "price": price,
                "reviews": reviews,
                "link": link
            })

        # Сортировка: по отзывам (↓), затем по цене (↑)
        result.sort(key=lambda x: (-x["reviews"], x["price"]))
        return result[:5]  # ТОП-5

    except Exception as e:
        logger.error(f"💥 Ошибка при запросе к прокси: {e}")
        return None  # Ошибка — фолбэк покажет ссылку

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

    # === ФОЛБЭК: если прокси не ответил ===
    if results is None:
        encoded_query = urllib.parse.quote(query)
        wb_link = f"https://www.wildberries.ru/catalog/0/search.aspx?search={encoded_query}"

        await update.message.reply_text(
            f"⚠️ *Сервис временно недоступен*\n"
            f"Но вы можете вручную посмотреть лучшие предложения:\n\n"
            f"🔍 *{query} на Wildberries*\n"
            f"🔗 Перейти({wb_link})\n\n"
            f"🔄 Попробуйте позже — иногда сервера перегружены",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    elif results:
        message = "🏆 *ТОП-5 самых популярных товаров:*\n\n"
        for i, r in enumerate(results, 1):
            stars = "⭐" * min(5, max(1, r['reviews'] // 50))
            message += (
                f"{i}. *{r['name']}*\n"
                f" 💰 {r['price']:,} ₽ | {r['reviews']} отзывов {stars}\n"
                f" 🔗 Перейти({r['link']})\n\n"
            )
        await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

    else:
        await update.message.reply_text(
            "❌ По вашему запросу ничего не найдено.\n\n"
            "Попробуйте:\n"
            "• Уточнить запрос (например, «кроссовки мужские»)\n"
            "• Написать по-другому («наушники» → «наушники беспроводные»)\n"
            "• Попробовать позже"
        )

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

