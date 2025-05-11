import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramNetworkError

# Токен бота
BOT_TOKEN = "7619827644:AAG7b9njo-8LqqzsqQX1n0t-Af4J5CROyAg"

# Инициализация бота с увеличенным таймаутом
bot = Bot(token=BOT_TOKEN, timeout=30)
dp = Dispatcher()


# Подключение к базам данных с Row factory
def get_products_db():
    conn = sqlite3.connect('products.db')
    conn.row_factory = sqlite3.Row  # Для доступа к полям по имени
    return conn


def get_clients_db():
    conn = sqlite3.connect('clients.db')
    conn.row_factory = sqlite3.Row
    return conn


# Клавиатура главного меню
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛍 Товары", callback_data="products"),
        InlineKeyboardButton(text="👥 Клиенты", callback_data="clients")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ О боте", callback_data="about"),
        InlineKeyboardButton(text="➕ Добавить товар", callback_data="add_product")
    )
    return builder.as_markup()


# ========== ОБРАБОТЧИКИ КОМАНД ==========

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в систему управления магазином!",
        reply_markup=main_menu()
    )


# ========== ОБРАБОТЧИКИ РАЗДЕЛОВ ==========

@dp.callback_query(F.data == "products")
async def show_products(callback: types.CallbackQuery):
    conn = get_products_db()
    try:
        products = conn.execute("SELECT name, price FROM products LIMIT 5").fetchall()

        if not products:
            await callback.message.edit_text("Товаров нет в базе!", reply_markup=main_menu())
            return

        text = "🛍 Последние товары:\n\n" + "\n".join(
            f"{p['name']} - {p['price']}₽" for p in products
        )
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        text += f"\n\nВсего товаров: {count}"

        await callback.message.edit_text(text, reply_markup=main_menu())
    except Exception as e:
        await callback.message.edit_text(f"Ошибка: {str(e)}", reply_markup=main_menu())
    finally:
        conn.close()
    await callback.answer()


@dp.callback_query(F.data == "clients")
async def show_clients(callback: types.CallbackQuery):
    conn = get_clients_db()
    try:
        clients = conn.execute("SELECT full_name, phone FROM clients LIMIT 5").fetchall()

        if not clients:
            await callback.message.edit_text("Клиентов нет в базе!", reply_markup=main_menu())
            return

        text = "👥 Последние клиенты:\n\n" + "\n".join(
            f"{c['full_name']} - {c['phone']}" for c in clients
        )
        count = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
        text += f"\n\nВсего клиентов: {count}"

        await callback.message.edit_text(text, reply_markup=main_menu())
    except Exception as e:
        await callback.message.edit_text(f"Ошибка: {str(e)}", reply_markup=main_menu())
    finally:
        conn.close()
    await callback.answer()


@dp.callback_query(F.data == "about")
async def show_about(callback: types.CallbackQuery):
    text = (
        "🤖 Бот для управления магазином\n\n"
        "Функции:\n"
        "- Просмотр товаров\n"
        "- Управление клиентами\n"
        "- Статистика продаж\n\n"
        "Версия: 1.0"
    )
    await callback.message.edit_text(text, reply_markup=main_menu())
    await callback.answer()


@dp.callback_query(F.data == "add_product")
async def add_product_start(callback: types.CallbackQuery):
    await callback.message.answer("Введите название нового товара:")
    await callback.answer()


# ========== ЗАПУСК БОТА ==========
async def main():
    # Удаляем вебхук перед запуском polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("Вебхук успешно удален")
    except TelegramNetworkError as e:
        print(f"Ошибка при удалении вебхука: {e}")
        exit(1)

    # Проверка подключения к БД
    try:
        with get_products_db() as conn:
            conn.execute("SELECT 1 FROM products LIMIT 1")
        print("✅ База товаров подключена")

        with get_clients_db() as conn:
            conn.execute("SELECT 1 FROM clients LIMIT 1")
        print("✅ База клиентов подключена")
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        exit(1)

    print("🟢 Бот запускается...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
    except Exception as e:
        print(f"Критическая ошибка: {e}")