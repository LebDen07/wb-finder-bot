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

# === Поиск через API Wildberries с улучшенным User-Agent и логированием ===
def search_wb(query: str) -> list:
    # Резервные URL (если один не работает)
    urls = [
        f"https://search.wb.ru/exactmatch/ru/common/v4/search?query={query}&resultset=catalog",
        f"https://search.wb.ru/exactmatch/ru/search/m/catalog?query={query}",
        f"https://search.wb.ru/suggestions/ru/catalog?query={query}"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.wildberries.ru/",
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site"
    }

    for url in urls:
        try:
            logger.info(f"🔍 Отправляю запрос к Wildberries: {url}")
            response = requests.get(url, headers=headers, timeout=15)

            logger.info(f"📡 Статус ответа: {response.status_code}")

            if response.status_code != 200:
                logger.warning(f"⚠️ Ошибка: статус {response.status_code} для {url}")
                continue

            # Попробуем распарсить JSON
            try:
                data = response.json()
            except Exception as e:
                logger.error(f"❌ Не удалось распарсить JSON: {e}")
                continue

            # Проверяем, есть ли данные
            products = data.get("data", {}).get("products", []) or data.get("products", [])
            if not products:
                logger.warning(f"📦 Нет товаров в ответе для: {url}")
                continue

            logger.info(f"✅ Найдено {len(products)} товаров")

            results = []
            for p in products[:20]:
                try:
                    price_u = p.get("salePriceU") or p.get("priceU")
                    if not price_u:
                        continue

                    price = price_u // 100
                    reviews = p.get("reviewCount", 0) or p.get("feedbacks", 0)
                    name = p.get("name", "Без названия") or p.get("productName", "Без названия")
                    product_id = p.get("id") or p.get("nmId")
                    if not product_id:
                        continue

                    link = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"

                    if len(name) > 100 or "доставка" in name.lower():
                        continue

                    results.append({
                        "name": name,
                        "price": price,
                        "reviews": reviews,
                        "link": link
                    })
                except Exception as e:
                    logger.error(f"❌ Ошибка при обработке товара: {e}")
                    continue

            # Сортировка: по отзывам (↓), потом цена (↑)
            results.sort(key=lambda x: (-x["reviews"], x["price"]))
            return results[:5]

        except requests.exceptions.ConnectionError as e:
            logger.error(f"🌐 Ошибка подключения к {url}: {e}")
            continue
        except requests.exceptions.Timeout as e:
            logger.error(f"⏰ Таймаут при запросе к {url}: {e}")
            continue
        except Exception as e:
            logger.error(f"❌ Неизвестная ошибка при запросе: {e}")
            continue

    logger.error("❌ Все URL не вернули результаты")
    return []

# === Команда /start ===
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
            "❌ Ничего не найдено по запросу *«{query}»*.\n\n"
            "Попробуй уточнить: например, *«кроссовки мужские»*, *«наушники Bluetooth»*."
        ).format(query=query)

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
