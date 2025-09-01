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

if not TOKEN:
    logger.error("❗ TELEGRAM_TOKEN не задан. Установите в переменных окружения Render.")
else:
    logger.info("✅ TELEGRAM_TOKEN загружен")

# === Flask-сервер для поддержания активности (чтобы Render не "убил" процесс) ===
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

# === Поиск товаров через API Wildberries (с фильтрами) ===
def search_wb(query: str) -> list:
    url = "https://search.wb.ru/exactmatch/ru/common/v4/search"
    params = {
        "query": query,
        "resultset": "catalog",
        "dest": "-1257786",
        "appType": "1",
        "sort": "popular",
        "spp": "0"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.wildberries.ru/",
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        logger.info(f"🔍 Отправляю запрос: {url}?query={query}")
        response = requests.get(url, params=params, headers=headers, timeout=15)

        logger.info(f"📡 Статус ответа: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"❌ Ошибка API: {response.status_code}")
            return []

        try:
            data = response.json()
        except Exception as e:
            logger.error(f"❌ Не удалось распарсить JSON: {e}")
            return []

        products = data.get("data", {}).get("products", [])
        if not products:
            logger.warning("📦 Нет товаров в ответе")
            return []

        logger.info(f"✅ Найдено {len(products)} товаров")

        results = []
        for p in products[:50]:  # Берём больше, чтобы отфильтровать
            try:
                # Оценка (rating) = reviewCount / feedbacks (если нет — пропускаем)
                feedbacks = p.get("reviewCount", 0) or p.get("feedbacks", 0)
                price_u = p.get("salePriceU") or p.get("priceU")
                if not price_u or feedbacks < 5:  # минимум 5 отзывов
                    continue

                # Рассчитываем рейтинг (если есть)
                rating = p.get("reviewRating", 0)
                if rating < 4.7:
                    continue

                price = price_u // 100
                name = p.get("name") or p.get("productName", "Без названия")
                product_id = p.get("id") or p.get("nmId")
                if not product_id:
                    continue

                link = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"

                if len(name) > 100 or "доставка" in name.lower():
                    continue

                results.append({
                    "name": name,
                    "price": price,
                    "reviews": feedbacks,
                    "rating": rating,
                    "link": link
                })
            except Exception as e:
                logger.error(f"❌ Ошибка при обработке товара: {e}")
                continue

        # Сортировка: по отзывам (↓), затем цена (↑)
        results.sort(key=lambda x: (-x["reviews"], x["price"]))
        return results[:5]

    except Exception as e:
        logger.error(f"❌ Ошибка запроса: {e}")
        return []

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔍 Начать поиск", callback_data="start_searching")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎉 *Привет! Добро пожаловать в бот по поиску самых выгодных цен на Wildberries!* 🛍️\n\n"
        "🔥 Здесь ты найдёшь:\n"
        "✅ *Топовые товары* с рейтингом от 4.7 ⭐\n"
        "💬 *Наибольшее количество отзывов* 📣\n"
        "💰 *Максимальные скидки* и лучшие цены 💸\n\n"
        "📌 Подпишись на канал: [*Лучшее с Wildberries | DenShop1*](https://t.me/+uGrNl01GXGI4NjI6)\n"
        "🚀 Просто нажми кнопку ниже и начни экономить уже сейчас!",
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

# === Обработчик кнопки ===
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

# === Обработка текстового запроса ===
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
        message = "🏆 *Топ-5 самых выгодных предложений (рейтинг ≥ 4.7, много отзывов):*\n\n"
        for i, r in enumerate(results, 1):
            stars = "⭐" * 5  # Все товары ≥ 4.7
            message += (
                f"{i}. *{r['name']}*\n"
                f"   💰 {r['price']:,.0f} ₽  |  {r['reviews']} отзывов  {stars}\n"
                f"   🔗 [Перейти]({r['link']})\n\n"
            )
    else:
        # 🔗 Ссылка на Wildberries с фильтрами
        wb_link = f"https://www.wildberries.ru/catalog/0/search.aspx?search={query}&sort=popular&rating=4.7"
        message = (
            "❌ Ничего не найдено по запросу *«{query}»*.\n\n"
            "Попробуй поискать на официальном сайте с фильтрами:\n"
            "• Сортировка: по популярности\n"
            "• Рейтинг: от 4.7\n"
            "• Много отзывов\n\n"
            "🛒 [Перейти на Wildberries]({link})"
        ).format(query=query, link=wb_link)

    await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

# === Запуск бота ===
if __name__ == "__main__":
    keep_alive()  # Запускаем Flask-сервер

    if not TOKEN:
        logger.error("❗ Бот не может запуститься: не задан TELEGRAM_TOKEN")
    else:
        logger.info("🤖 Бот запускается...")
        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("✅ Бот запущен и слушает сообщения...")
        app.run_polling()
