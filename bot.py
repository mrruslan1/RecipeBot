import telebot
import requests
from telebot import types

TOKEN = '8876162909:AAGMh1SUrjw0T8PdpojVJ1nkvjoMG6UWQVU'
bot = telebot.TeleBot(TOKEN)

def get_random_recipe():
    url = 'https://www.themealdb.com/api/json/v1/1/random.php'
    response = requests.get(url).json()
    meal = response['meals'][0]
    
    # Проверяем наличие ссылки, если её нет — ставим заглушку
    link = meal.get("strSource") or "https://www.themealdb.com"
    
    return {
        "title": meal["strMeal"],
        "category": meal["strCategory"],
        "area": meal["strArea"],
        "image_url": meal["strMealThumb"],
        "link": link
    }

def search_recipes(ingredient):
    url = f'https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient}'
    response = requests.get(url).json()
    
    meals = []
    # Если ингредиент не найден, API возвращает None
    if response.get('meals') is None:
        return meals
        
    for item in response.get('meals', []):
        meals.append({
            "title": item["strMeal"],
            "image_url": item["strMealThumb"],
            "id": item["idMeal"]
        })
    
    return meals[:5]


def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_random = types.KeyboardButton("🎲 Случайный рецепт")
    btn_search = types.KeyboardButton("🔍 Как искать?")
    markup.add(btn_random, btn_search)
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "🍲 Привет! Я кулинарный бот.\n\n"
        "Вы можете использовать меню внизу или команды:\n"
        "/random — получить случайное блюдо\n"
        "Просто напиши мне любой продукт или слово на английском, чтобы найти рецепт.",
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(commands=['random'])
def send_random_recipe(message):
    recipe = get_random_recipe()

    text = (
        f"<b>{recipe['title']}</b>\n"
        f"🌐 <a href='{recipe['link']}'>Полный рецепт</a>\n"
        f"Категория: {recipe['category']} | Страна: {recipe['area']}"
    )

    bot.send_photo(
        chat_id=message.chat.id,
        photo=recipe["image_url"],
        caption=text,
        parse_mode="HTML",
    )

# Обработка текстовых сообщений (включая нажатия на Reply-кнопки)
@bot.message_handler(content_types=["text"])
def handle_text(message):
    text_input = message.text.strip()

    # Проверяем нажатие кнопки "Случайный рецепт"
    if text_input == "🎲 Случайный рецепт":
        return send_random_recipe(message)
    
    # Проверяем нажатие кнопки "Как искать?"
    if text_input == "🔍 Как искать?":
        return bot.send_message(
            message.chat.id, 
            "Введите название основного ингредиента на английском языке (например: <b>chicken</b>, <b>beef</b>, <b>tomato</b>), и я подберу рецепты!",
            parse_mode="HTML"
        )

    # Обычный текстовый поиск ингредиента
    ingredient = text_input.lower()
    recipes = search_recipes(ingredient)
    if not recipes:
        return bot.reply_to(message, "🚫 Рецепты не найдены. Попробуйте на английском (например: chicken, pork).")

    markup = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        types.InlineKeyboardButton(recipe["title"], callback_data=f'recipe_{recipe["id"]}')
        for recipe in recipes
    ]
    markup.add(*buttons)

    bot.send_message(
        message.chat.id,
        f"🥗 Вот что я нашел по запросу '{ingredient}':",
        reply_markup=markup
    )

# Важно: callback_query_handler должен быть ДО запуска polling
@bot.callback_query_handler(func=lambda call: True)
def show_full_recipe(call):
    _, recipe_id = call.data.split('_')

    url = f'https://www.themealdb.com/api/json/v1/1/lookup.php?i={recipe_id}'
    response = requests.get(url).json()
    meal = response['meals'][0]

    ingredients = []
    for i in range(20):
        ing = meal.get(f'strIngredient{i + 1}')
        meas = meal.get(f'strMeasure{i + 1}')
        # Защита от пустых строк и None значений из API
        if ing and ing.strip():
            meas_str = f" ({meas.strip()})" if meas and meas.strip() else ""
            ingredients.append(f"- {ing.strip()}{meas_str}")

    link = meal.get("strSource") or "https://www.themealdb.com"

    text = (
        f"<b>{meal['strMeal']}</b>\n"
        f"🌐 <a href='{link}'>Полный рецепт</a>\n\n"
        "<u>Ингредиенты (первые 5):</u>\n" + "\n".join(ingredients[:5])
    )

    try:
        # Изменяем картинку на картинку выбранного блюда
        bot.edit_message_media(
            media=types.InputMediaPhoto(meal["strMealThumb"]),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        # Изменяем текст и убираем инлайн-кнопки поиска
        bot.edit_message_caption(
            caption=text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка обновления сообщения: {e}")
        # Если старое сообщение было чисто текстовым, edit_message_media вызовет ошибку. 
        # На всякий случай отправляем рецепт новым сообщением.
        bot.send_photo(
            chat_id=call.message.chat.id,
            photo=meal["strMealThumb"],
            caption=text,
            parse_mode="HTML"
        )
    
    # Уведомляем Telegram, что кнопка успешно обработана (убирает вечную загрузку на кнопке)
    bot.answer_callback_query(call.id)

# Точка входа внизу файла
if __name__ == "__main__":
    print("Бот запущен!")
    bot.infinity_polling()
