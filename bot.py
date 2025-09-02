# wb_finder_bot.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

# ⚙️ Настройки
TELEGRAM_TOKEN = "8359908342:AAFT5jgAHvDo5wnuZqZEM1A4OkboU4TE4IU"  # 🔥 Замените на свой!
SEARCH_BASE = "https://www.wildberries.ru/catalog/0/search.aspx?search="

# 🛠️ Настройка драйвера
def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # фоновый режим
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => false});")
    return driver

# 🔍 Улучшенный парсинг цены и отзывов
def parse_price_and_reviews(product):
    price = None
    reviews = 0

    # 💰 Парсинг цены
    try:
        main_price_elem = product.find_element(By.XPATH, './/span[contains(@class, "price") and not(contains(@class, "old"))]')
        price_text = main_price_elem.text.strip()
        price_match = re.search(r'\d+', price_text.replace(' ', ''))
        if price_match:
            price = int(price_match.group())
    except:
        pass

    if not price:
        try:
            all_prices = product.find_elements(By.XPATH, './/span[contains(text(), "₽")]')
            for el in all_prices:
                txt = el.text.strip()
                match = re.search(r'\d+', txt.replace(' ', ''))
                if match:
                    price = int(match.group())
                    break
        except:
            pass

    # ⭐ Парсинг отзывов — ищем по всей карточке
    try:
        # Вариант 1: REVMT или текст с отзывами
        review_elements = product.find_elements(By.XPATH,
            './/span[contains(text(), "отзыв") or contains(text(), "review") or contains(text(), "REVMT")] | '
            './/div[contains(text(), "отзыв") or contains(text(), "review") or contains(text(), "REVMT")]'
        )
        for el in review_elements:
            text = el.text.strip()
            match = re.search(r'\d+', text)
            if match:
                reviews = int(match.group())
                break

        # Вариант 2: по классу (count, reviews)
        if reviews == 0:
            count_elems = product.find_elements(By.XPATH,
                './/*[contains(@class, "count") or contains(@class, "reviews") or contains(@class, "revmt")]'
            )
            for el in count_elems:
                text = el.get_attribute("textContent").strip()
                match = re.search(r'\d+', text)
                if match:
                    reviews = int(match.group())
                    break

        # Вариант 3: data-count
        if reviews == 0:
            try:
                data_count = product.get_attribute("data-count")
                if data_count and data_count.isdigit():
                    reviews = int(data_count)
            except:
                pass

        # Вариант 4: REVMT в тексте карточки
        if reviews == 0:
            full_text = product.text
            match = re.search(r'REVMT\D*(\d+)', full_text, re.IGNORECASE)
            if match:
                reviews = int(match.group(1))

    except Exception as e:
        pass

    return price, reviews

# 🔎 Поиск на Wildberries
def search_wb(query: str) -> list:
    driver = create_driver()
    results = []
    url = SEARCH_BASE + query.replace(" ", "+")
    
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article.product-card"))
        )
        products = driver.find_elements(By.CSS_SELECTOR, "article.product-card")
        
        for product in products[:20]:
            try:
                link_elem = product.find_element(By.CSS_SELECTOR, "a[href*='/catalog/']")
                name = link_elem.get_attribute("aria-label")
                if not name or len(name) > 100 or "доставка" in name.lower():
                    continue

                # Передаём всю карточку
                price, reviews = parse_price_and_reviews(product)

                if not price:
                    continue

                link = link_elem.get_attribute("href")

                results.append({
                    "name": name,
                    "price": price,
                    "reviews": reviews,
                    "link": link
                })
            except Exception as e:
                continue

        # Сортировка: больше отзывов → дешевле
        results.sort(key=lambda x: (-x["reviews"], x["price"]))

    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")
    finally:
        driver.quit()

    return results[:5]

# 🤖 Команда /start с анимацией, ссылкой и кнопкой
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Кнопка
    keyboard = [[InlineKeyboardButton("🔍 Начать поиск", callback_data="start_searching")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Текст с гиперссылкой на канал
    await update.message.reply_text(
        "🎉 *Привет! Добро пожаловать в бот по поиску самых выгодных цен на Wildberries!* 🛍️\n\n"
        "🔥 Здесь ты найдёшь:\n"
        "✅ *Топовые товары* с самыми высокими оценками ⭐\n"
        "💰 *Максимальные скидки* и лучшие цены 💸\n"
        "📦 *Проверенные отзывы* от тысяч покупателей 📣\n\n"
        "📌 Подпишись на канал: [*Лучшее с Wildberries | DenShop1*](https://t.me/+uGrNl01GXGI4NjI6)\n"
        "Там — только самые горячие скидки и лайфхаки по покупкам! 🔥\n\n"
        "🚀 Просто нажми кнопку ниже и начни экономить уже сейчас!",
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

# 🤖 Обработчик кнопки
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

# 🤖 Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if len(query) < 2:
        await update.message.reply_text("❌ Запрос слишком короткий.")
        return

    # Сообщение с гиперссылкой на канал
    await update.message.reply_text(
        f"🔥 [*Лучшее с Wildberries | DenShop1*](https://t.me/+uGrNl01GXGI4NjI6)\n"
        f"Ищу: *{query}*",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

    results = search_wb(query)

    if results:
        message = "🏆 *Топ-5 самых выгодных предложений:*\n\n"
        for i, r in enumerate(results, 1):
            stars = "⭐" * min(5, max(1, (r['reviews'] // 50)))
            message += (
                f"{i}. *{r['name']}*\n"
                f"   💰 {r['price']:,.0f} ₽  |  {r['reviews']} отзывов  {stars}\n"
                f"   🔗 [Перейти]({r['link']})\n\n"
            )
    else:
        message = "❌ Ничего не найдено. Попробуй уточнить запрос."

    await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

# 🚀 Запуск
if __name__ == "__main__":
    print("🤖 Бот запускается...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Бот запущен. Готов к поиску...")
    app.run_polling()
