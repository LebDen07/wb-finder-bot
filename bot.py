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

# Токен из переменной окружения
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

# === Поиск товаров на OZON через прокси ===
def search_ozon(query: str) -> list:
 if not query.strip():
 return 

 logger.info(f"🔍 Поиск на OZON: '{query}'")
 encoded_query = urllib.parse.quote(query.strip())
 proxy_url = f"https://ozon-api-proxy.vercel.app/api/search?q={encoded_query}"

 try:
 response = requests.get(
 proxy_url,
 timeout=15,
 headers={
 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
 "Accept": "application/json",
 "Referer": "https://ozon-api-proxy.vercel.app"
 }
 )

 logger.info(f"📊 Статус прокси: {response.status_code}")

 if response.status_code != 200:
 logger.error(f"❌ Ошибка прокси: {response.status_code}")
 return None

 data = response.json()

 if not data.get("products") or not isinstance(data"products", list):
 logger.warning("📦 Нет товаров в ответе или формат неверен")
 return 

 products = data"products"
 result = 
 seen_ids = set()

 for p in products:50:
 try:
 pid = p.get("id")
 if not pid or pid in seen_ids:
 continue
 seen_ids.add(pid)

 price = p.get("price")
 if not price or price <= 0:
 continue

 reviews = p.get("reviews", 0)
 name = p.get("name", "").strip()
 brand = p.get("brand", "").strip()
 if not name:
 continue

 full_name = f"{brand} {name}".strip()
 if len(full_name) > 80:
 full_name = full_name:77 + "..."

 # Ссылка на товар OZON
 link = f"https://www.ozon.ru/product/{pid}/"

 result.append({
 "name": full_name,
 "price": price,
 "reviews": reviews,
 "link": link
 })
 except (TypeError, ValueError, AttributeError):
 continue

 if not result:
 return 

 # Сортировка: по отзывам (↓), цена (↑)
 result.sort(key=lambda x: (-x"reviews", x"price"))
 return result:5 # ТОП-5

 except Exception as e:
 logger.error(f"💥 Ошибка при запросе к OZON прокси: {e}")
 return None

# === Обработчики ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
 keyboard = InlineKeyboardButton("🔍 Начать поиск", callback_data="start_searching")
 reply_markup = InlineKeyboardMarkup(keyboard)

 await update.message.reply_text(
 "🎉 *Привет Добро пожаловать в бот по поиску лучших цен на OZON!* 🛍️\n\n"
 "🔥 Здесь ты найдёшь:\n"
 "✅ *Топовые товары* с высокими оценками ⭐\n"
 "💰 *Лучшие цены* и скидки 💸\n"
 "📦 *Много отзывов* — проверено тысячами покупателей 📣\n\n"
 "📌 Подпишись на канал: *Лучшее с OZON | DenShop1*(https://t.me/+uGrNl01GXGI4NjI6)\n"
 "Там — только горячие скидки и лайфхаки 🔥\n\n"
 "🚀 Нажми кнопку и начни экономить!",
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
 "Теперь напиши, что ты хочешь найти на OZON.\n\n"
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
 f"🔥 *Лучшее с OZON | DenShop1*(https://t.me/+uGrNl01GXGI4NjI6)\n"
 f"🔍 Ищу *ТОПовые товары* по запросу: *{query}*",
 parse_mode="Markdown",
 disable_web_page_preview=True
 )

 # Ищем
 results = search_ozon(query)

 # === ФОЛБЭК: если прокси не ответил ===
 if results is None:
 encoded_query = urllib.parse.quote(query)
 ozon_link = f"https://www.ozon.ru/search/?text={encoded_query}"

 await update.message.reply_text(
 f"⚠️ *Сервис временно недоступен*\n"
 f"Но вы можете посмотреть вручную:\n\n"
 f"🔍 *{query} на OZON*\n"
 f"🔗 Перейти({ozon_link})\n\n"
 f"🔄 Попробуйте позже"
 ,
 parse_mode="Markdown",
 disable_web_page_preview=True
 )

 elif results:
 message = "🏆 *ТОП-5 самых популярных товаров на OZON:*\n\n"
 for i, r in enumerate(results, 1):
 stars = "⭐" * min(5, max(1, r'reviews' // 50))
 message += (
 f"{i}. *{r'name'}*\n"
 f" 💰 {r'price':,} ₽ | {r'reviews'} отзывов {stars}\n"
 f" 🔗 Перейти({r'link'})\n\n"
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

 logger.info("🤖 Инициализация бота для OZON...")
 application = Application.builder().token(TOKEN).build()

 application.add_handler(CommandHandler("start", start))
 application.add_handler(CallbackQueryHandler(button_handler))
 application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

 logger.info("✅ Бот для OZON запущен. Ожидание сообщений...")

 try:
 asyncio.run(application.run_polling())
 except KeyboardInterrupt:
 logger.info("💤 Бот остановлен вручную.")
 except Exception as e:
 logger.critical(f"💥 Критическая ошибка: {e}")
