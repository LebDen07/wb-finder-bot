# bot.py
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, CallbackContext
from flask import Flask
from threading import Thread
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    logger.error("❗ TELEGRAM_TOKEN не задан")
else:
    logger.info("✅ TELEGRAM_TOKEN загружен")

# === Flask для поддержания активности ===
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "✅ Бот работает 24/7"

def run():
    port = int(os.getenv('PORT', 8080))
    app_flask.run(host='0.0.0.0', port=port)

def keep_alive():
    logger.info("🚀 Запускаем Flask-сервер...")
    t = Thread(target=run)
    t.daemon = True
    t.start()

# === Категории ===
CATEGORIES = {
    "Наушники": {
        "Беспроводные": "наушники+беспроводные",
        "Проводные": "наушники+проводные",
        "Вкладыши": "наушники+вкладыши",
        "Накладные": "наушники+накладные"
    },
    "Кроссовки": {
        "Мужские": "кроссовки+мужские",
        "Женские": "кроссовки+женские",
        "Детские": "кроссовки+детские",
        "Спортивные": "кроссовки+спортивные"
    },
    "Смартфоны": {
        "До 20000₽": "смартфон+до+20000",
        "До 30000₽": "смартфон+до+30000",
        "Флагманы": "смартфон+флагман",
        "5G": "смартфон+5g"
    }
}

# === Начало: /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for category in CATEGORIES:
        keyboard.append([InlineKeyboardButton(category, callback_data=f"cat_{category}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🛒 Добро пожаловать в бот по поиску товаров на Wildberries!\n\n"
        "Выберите категорию:",
        reply_markup=reply_markup
    )

# === Обработка нажатий ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("cat_"):
        category = data.replace("cat_", "")
        context.user_data['category'] = category

        keyboard = []
        for subcat, query_str in CATEGORIES[category].items():
            keyboard.append([InlineKeyboardButton(subcat, callback_data=f"sub_{query_str}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_start")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Вы выбрали: *{category}*\n\nВыберите подкатегорию:", reply_markup=reply_markup, parse_mode="Markdown")

    elif data.startswith("sub_"):
        search_query = data.replace("sub_", "")
        context.user_data['search_query'] = search_query

        # Генерируем ссылку с фильтрами
        encoded_query = search_query.replace(" ", "+")
        wb_link = f"https://www.wildberries.ru/catalog/0/search.aspx?search={encoded_query}&sort=popular&rating=4.7"

        # Пример товара (можно заменить на парсинг, но пока mock)
        product = {
            "title": f"Лучшие {search_query.replace('+', ' ')}",
            "price": "от 1999₽",
            "rating": "4.8",
            "reviews": "150+",
            "image": "https://via.placeholder.com/200x200.png?text=WB"
        }

        message = (
            f"🔍 *Найдено по запросу:* `{search_query}`\n\n"
            f"🛍️ *{product['title']}*\n"
            f"💰 Цена: *{product['price']}*\n"
            f"⭐ Рейтинг: *{product['rating']}* ({product['reviews']} отзывов)\n\n"
            f"[🛒 Перейти к товарам]({wb_link})"
        )

        keyboard = [
            [InlineKeyboardButton("🔄 Новый поиск", callback_data="back_start")],
            [InlineKeyboardButton("📌 Подписаться", url="https://t.me/+uGrNl01GXGI4NjI6")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown", disable_web_page_preview=False)

    elif data == "back_start":
        await start(update, context)

# === Запуск бота ===
if __name__ == "__main__":
    keep_alive()

    if not TOKEN:
        logger.error("❗ Бот не может запуститься: не задан TELEGRAM_TOKEN")
    else:
        logger.info("🤖 Бот запускается...")
        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))

        logger.info("✅ Бот запущен и слушает сообщения...")
        app.run_polling()
