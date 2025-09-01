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

# 🔍 Проверка версии Python — критично для совместимости
print(f"🐍 Используется Python: {sys.version}")

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменной окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    logger.error("❗ ОШИБКА: Не задан TELEGRAM_TOKEN. Установите переменную окружения в Render.")
    sys.exit(1)
else:
    logger.info("✅ TELEGRAM_TOKEN загружен")

# === Flask-сервер для keep-alive (Render не "усыпляет" сервис) ===
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "🟢 Wildberries Search Bot активен и работает 24/7"

def run_flask():
    port = int(os.getenv('PORT', 10000))
    logger.info(f"🚀 Flask-сервер запущен на порту {port}")
    app_flask.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def keep_alive():
    logger.info("🔧 Запускаем фоновый сервер для поддержания активности...")
    t = Thread(target=run_flask, daemon=True)
    t.start()

# === Поиск товаров Wildberries (ОБНОВЛЁННЫЙ, РАБОЧИЙ на 2025) ===
def search_wb(query: str) -> list:
    if not query.strip():
        return []

    # Основной рабочий URL (на 2025)
    url = "https://search.wb.ru/exactmatch/ru/common/v4/search"

    # Альтернативный URL, если основной блокируется
    alt_urls = [
        "https://wbxsearch.wb.ru/exactmatch/ru/common/v4/search",  # Зеркало
        "https://search.wb.ru/exactmatch/ru/male/v4/search",      # Альтернативный путь
    ]

    # Параметры запроса
    params = {
        "query": query.strip(),
        "resultset": "items",
        "limit": 100,
        "page": 1,
        "dest": -1257786,  # Россия
        "spp": 30,         # Скидка по карте
        "lang": "ru",
        "locale": "ru",
        "curr": "rub"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.wildberries.ru/",
        "Origin": "https://www.wildberries.ru",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "X-Requested-With": "XMLHttpRequest",
        "Cache-Control": "no-cache"
    }

    # Пробуем основной URL и альтернативы
    urls_to_try = [url] + alt_urls

    for attempt, current_url in enumerate(urls_to_try, 1):
        try:
            logger.info(f"🔍 Попытка {attempt}: Запрос к {current_url}")
            response = requests.get(current_url, params=params, headers=headers, timeout=12)

            logger.info(f"📊 Статус: {response.status_code} | URL: {response.url}")

            if response.status_code == 200:
                data = response.json()
                products = data.get("data", {}).get("products", [])
                if products:
                    logger.info(f"📦 Найдено {len(products)} товаров")
                    break
                else:
                    logger.warning(f"⚠️ Ничего не найдено по запросу: {query}")
                    continue
            else:
                logger.warning(f"❌ Ошибка API (статус {response.status_code}) на URL {current_url}")
                continue
        except Exception as e:
            logger.error(f"💥 Ошибка при запросе к {current_url}: {e}")
            continue
    else:
        logger.error("❌ Все URL не ответили или вернули пустые данные")
        return []

    # Обработка товаров
    results = []
    for p in products[:50]:
        price_u = p.get("salePriceU") or p.get("priceU") or p.get("finalPriceU")
        if not price_u:
            continue

        price = price_u // 100
        reviews = p.get("feedbackCount", 0)
        name = p.get("name", "Без названия") or p.get("product")
        brand = p.get("brand", "").strip()
        product_id = p.get("id")
        if not product_id:
            continue

        full_name = f"{brand} {name}".strip()
        link = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"

        # Фильтрация мусора
        if len(full_name) > 100 or any(word in full_name.lower() for word in ["доставка", "самовывоз", "под заказ"]):
            continue

        results.append({
            "name": full_name[:80] + "..." if len(full_name) > 80 else full_name,
            "price": price,
            "reviews": reviews,
            "link": link
        })

    # Сортировка: по отзывам (↓), потом цена (↑)
    results.sort(key=lambda x: (-x["reviews"], x["price"]))
    return results[:5]
# === Обработчики команд ===

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
        message = (
            "❌ Ничего не найдено. Попробуй:\n"
            "• Уточнить запрос (например, «кроссовки мужские»)\n"
            "• Написать по-другому («наушники» → «наушники беспроводные»)\n"
            "• Попробовать позже — возможно, временная блокировка"
        )

    await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)


# === Запуск бота ===
if __name__ == "__main__":
    # Запускаем Flask для keep-alive
    keep_alive()

    # Создаём приложение
    logger.info("🤖 Инициализация Telegram-бота...")
    application = Application.builder().token(TOKEN).build()

    # Добавляем хендлеры
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
