import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Токен бота
BOT_TOKEN = "7619827644:AAG7b9njo-8LqqzsqQX1n0t-Af4J5CROyAg"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Подключение к базам данных
def get_products_db():
    conn = sqlite3.connect('products.db')
    return conn


def get_clients_db():
    conn = sqlite3.connect('clients.db')
    return conn


# Клавиатура главного меню
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="🛍 Товары", callback_data="products"),
        types.InlineKeyboardButton(text="👥 Клиенты", callback_data="clients"),
        types.InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")
    )
    builder.adjust(2)
    return builder.as_markup()


# ========== ОБРАБОТЧИКИ КОМАНД ==========

# Стартовая команда
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в систему управления магазином!\n"
        "Выберите раздел:",
        reply_markup=main_menu()
    )


# ========== ОБРАБОТЧИКИ РАЗДЕЛОВ ==========

# Раздел товаров
@dp.callback_query(F.data == "products")
async def show_products(callback: types.CallbackQuery):
    conn = get_products_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT name, price FROM products LIMIT 5")
        products = cursor.fetchall()

        if not products:
            await callback.message.edit_text("Товаров нет в базе!")
            return

        text = "🛍 Последние товары:\n\n"
        text += "\n".join([f"{name} - {price}₽" for name, price in products])
        text += "\n\nВсего товаров: " + str(len(products))

        await callback.message.edit_text(
            text,
            reply_markup=main_menu()
        )
    finally:
        conn.close()

    await callback.answer()


# Раздел клиентов
@dp.callback_query(F.data == "clients")
async def show_clients(callback: types.CallbackQuery):
    conn = get_clients_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT full_name, phone FROM clients LIMIT 5")
        clients = cursor.fetchall()

        if not clients:
            await callback.message.edit_text("Клиентов нет в базе!")
            return

        text = "👥 Последние клиенты:\n\n"
        text += "\n".join([f"{name} - {phone}" for name, phone in clients])
        text += "\n\nВсего клиентов: " + str(len(clients))

        await callback.message.edit_text(
            text,
            reply_markup=main_menu()
        )
    finally:
        conn.close()

    await callback.answer()


# Информация о боте
@dp.callback_query(F.data == "about")
async def show_about(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🤖 Бот для управления магазином\n\n"
        "Функции:\n"
        "- Просмотр товаров\n"
        "- Управление клиентами\n"
        "- Статистика продаж",
        reply_markup=main_menu()
    )
    await callback.answer()


# ========== ЗАПУСК БОТА ==========
async def main():
    # Проверяем подключение к БД при старте
    try:
        with get_products_db() as conn:
            conn.execute("SELECT 1 FROM products LIMIT 1")
        with get_clients_db() as conn:
            conn.execute("SELECT 1 FROM clients LIMIT 1")
        print("Подключение к базам данных успешно!")
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        exit(1)

    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
