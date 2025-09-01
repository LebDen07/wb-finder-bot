# bot.py
import os
import sys
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

# Проверка Python
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

# === Кодировка запроса для URL ===
def url_encode(query: str) -> str:
 return urllib.parse.quote(query.strip())

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
 

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
 query = update.message.text.strip()
 if len(query) < 2:
 await update.message.reply_text("❌ Запрос слишком короткий. Введите хотя бы 2 символа.")
 return

 # Кодируем запрос
 encoded_query = url_encode(query)
 # Формируем ссылку на поиск Wildberries
 wb_url = f"https://www.wildberries.ru/catalog/0/search.aspx?search={encoded_query}"

 # Кнопка с ссылкой
 keyboard = InlineKeyboardButton("🛍 Перейти к товарам", url=wb_url)
 reply_markup = InlineKeyboardMarkup(keyboard)

 # Отправляем сообщение
 await update.message.reply_text(
 f"🔥 *Лучшее с Wildberries | DenShop1*(https://t.me/+uGrNl01GXGI4NjI6)\n\n"
 f"🔍 Вы искали: *{query}*\n\n"
 f"✅ Вот прямая ссылка на актуальные предложения —\n"
 f"только реальные товары, скидки и отзывы 💯",
 parse_mode="Markdown",
 disable_web_page_preview=True,
 reply_markup=reply_markup
 )

# === Запуск ===
if __name__ == "__main__":
 keep_alive()

 logger.info("🤖 Инициализация бота...")
 application = Application.builder().token(TOKEN).build()

 application.add_handler(CommandHandler("start", start))
 application.add_handler(CallbackQueryHandler(button_handler))
 application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

 logger.info("✅ Бот запущен")

 try:
 asyncio.run(application.run_polling())
 except KeyboardInterrupt:
 logger.info("💤 Остановлен")
 except Exception as e:
 logger.critical(f"💥 Ошибка: {e}")

