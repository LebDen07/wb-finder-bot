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

# === Поиск товаров — с фолбэком ===
def search_wb(query: str) -> list:
 if not query.strip():
 return 

 keyword = urllib.parse.quote(query.strip())
 logger.info(f"🔍 Поиск: '{query}'")

 # 🔁 Список URL для попыток (резервные варианты)
 urls = [
 f"https://catalog.wb.ru/catalog/autosearch/data?query={keyword}&dest=-1257786&lang=ru&curr=rub",
 f"https://catalog.wb.ru/catalog/electronics/catalog?keyword={keyword}&dest=-1257786&sort=popular",
 f"https://search.wb.ru/exactmatch/ru/common/v4/search?query={keyword}&dest=-1257786&resultset=items"
 ]

 headers = {
 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
 "Accept": "application/json",
 "Referer": "https://www.wildberries.ru/",
 "Origin": "https://www.wildberries.ru",
 "X-Requested-With": "XMLHttpRequest"
 }

 for i, url in enumerate(urls, 1):
 try:
 logger.info(f"🔁 Попытка {i}: GET {url}")
 response = requests.get(url, headers=headers, timeout=10)

 logger.info(f"📊 Статус: {response.status_code}")

 if response.status_code == 200:
 data = response.json()
 logger.info(f"📦 JSON получен: {len(str(data))} символов")

 products = 

 # Парсим разные форматы ответа
 if "data" in data and "products" in data"data":
 products = data"data""products"
 elif "data" in data and "items" in data"data":
 products = data"data""items"
 elif "products" in data:
 products = data"products"
 else:
 logger.warning(f"⚠️ Нет ключа 'products' в ответе")
 continue

 if products:
 logger.info(f"✅ Найдено {len(products)} товаров")
 result = 
 seen_ids = set()

 for p in products:50:
 pid = p.get("id") or p.get("nmId")
 if not pid or pid in seen_ids:
 continue
 seen_ids.add(pid)

 price_u = p.get("priceU") or p.get("salePriceU") or p.get("salePriceU")
 if not price_u:
 continue

 price = price_u // 100
 reviews = p.get("feedbacks", 0) or p.get("feedbackCount", 0)
 name = p.get("name", "Без названия")
 brand = p.get("brand", "").strip()
 full_name = f"{brand} {name}".strip():80
 link = f"https://www.wildberries.ru/catalog/{pid}/detail.aspx"

 result.append({
 "name": full_name,
 "price": price,
 "reviews": reviews,
 "link": link
 })

 result.sort(key=lambda x: (-x"reviews", x"price"))
 return result:5

 else:
 logger.warning(f"⚠️ Пустой список товаров в ответе")
 continue

 else:
 logger.warning(f"❌ Ошибка HTTP {response.status_code} на URL {url}")

 except Exception as e:
 logger.error(f"💥 Ошибка при запросе к {url}: {e}")
 continue

 # Если все API не ответили — возвращаем None (не пустой список!)
 logger.error("❌ Все API не ответили")
 return None  # Отличие: None = ошибка,  = пусто

# === Обработчики ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
 keyboard = InlineKeyboardButton("🔍 Начать поиск", callback_data="start_searching")
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

 # === ФОЛБЭК: если API не ответили (ошибка), но есть товары — показываем
 if results is None:
 # ❌ Все API упали — даём ручной поиск
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
 stars = "⭐" * min(5, max(1, r'reviews' // 50))
 message += (
 f"{i}. *{r'name'}*\n"
 f" 💰 {r'price':,} ₽ | {r'reviews'} отзывов {stars}\n"
 f" 🔗 Перейти({r'link'})\n\n"
 )
 await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

 else:
 # 📭 Пусто — но API ответил
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
