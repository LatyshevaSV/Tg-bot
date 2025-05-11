import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramNetworkError

# Токен бота
BOT_TOKEN = "7619827644:AAG7b9njo-8LqqzsqQX1n0t-Af4J5CROyAg"

# Инициализация бота с увеличенным таймаутом
bot = Bot(token=BOT_TOKEN, timeout=30)
dp = Dispatcher()

# Константы для пагинации
ITEMS_PER_PAGE = 5


# Подключение к базам данных с Row factory
def get_products_db():
    conn = sqlite3.connect('products.db')
    conn.row_factory = sqlite3.Row
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


# ========== КОМАНДЫ ДЛЯ ТОВАРОВ ==========

@dp.message(Command("products"))
async def cmd_products(message: types.Message):
    """Команда для вывода всех товаров"""
    await show_products_page(message, page=0)


@dp.message(Command("categories"))
async def cmd_categories(message: types.Message):
    """Команда для вывода категорий товаров"""
    conn = get_products_db()
    try:
        categories = conn.execute(
            "SELECT DISTINCT category FROM products"
        ).fetchall()

        if not categories:
            await message.answer("📂 Категории не найдены")
            return

        builder = InlineKeyboardBuilder()
        for category in categories:
            builder.add(InlineKeyboardButton(
                text=category['category'],
                callback_data=f"category_{category['category']}"
            ))
        builder.adjust(2)

        await message.answer(
            "📂 Выберите категорию:",
            reply_markup=builder.as_markup()
        )
    finally:
        conn.close()


# ========== ОБРАБОТЧИКИ ТОВАРОВ ==========

async def show_products_page(message: types.Message, page: int):
    """Показывает страницу с товарами"""
    conn = get_products_db()
    try:
        offset = page * ITEMS_PER_PAGE
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, price FROM products LIMIT ? OFFSET ?",
            (ITEMS_PER_PAGE, offset)
        )
        products = cursor.fetchall()

        total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]

        if not products:
            await message.answer("🛒 Товары не найдены")
            return

        text = f"📦 Товары (страница {page + 1}/{(total // ITEMS_PER_PAGE) + 1}):\n\n"
        for product in products:
            text += f"{product['id']}. {product['name']} - {product['price']}₽\n"

        builder = InlineKeyboardBuilder()

        if page > 0:
            builder.add(InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"products_page_{page - 1}"
            ))

        if (page + 1) * ITEMS_PER_PAGE < total:
            builder.add(InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"products_page_{page + 1}"
            ))

        await message.answer(text, reply_markup=builder.as_markup())

    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)}")
    finally:
        conn.close()


@dp.callback_query(F.data.startswith("products_page_"))
async def change_products_page(callback: types.CallbackQuery):
    """Обработчик переключения страниц товаров"""
    page = int(callback.data.split("_")[-1])
    await callback.message.delete()
    await show_products_page(callback.message, page)
    await callback.answer()


@dp.callback_query(F.data.startswith("category_"))
async def show_category_products(callback: types.CallbackQuery):
    """Показывает товары выбранной категории"""
    category = callback.data.split("_", 1)[1]
    conn = get_products_db()
    try:
        products = conn.execute(
            "SELECT name, price FROM products WHERE category = ?",
            (category,)
        ).fetchall()

        if not products:
            await callback.message.edit_text(f"🛒 В категории '{category}' нет товаров")
            return

        text = f"📦 Товары в категории '{category}':\n\n"
        text += "\n".join([f"{p['name']} - {p['price']}₽" for p in products])

        await callback.message.edit_text(text, reply_markup=main_menu())
    finally:
        conn.close()
    await callback.answer()


# ========== СТАРЫЕ ОБРАБОТЧИКИ (оставьте без изменений) ==========

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в систему управления магазином!",
        reply_markup=main_menu()
    )


@dp.callback_query(F.data == "products")
async def show_products(callback: types.CallbackQuery):
    try:
        with get_products_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, price, category FROM products LIMIT 5")
            products = cursor.fetchall()

            if not products:
                await callback.answer("ℹ️ Нет доступных товаров", show_alert=True)
                return

            response = "🛍 Товары:\n\n" + "\n".join(
                f"{p['name']} - {p['price']}₽ ({p['category']})"
                for p in products
            )

            count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            response += f"\n\nВсего товаров: {count}"

            await callback.message.edit_text(response, reply_markup=main_menu())

    except sqlite3.Error as e:
        await callback.answer(f"⛔ Ошибка БД: {e}", show_alert=True)
    except Exception as e:
        await callback.answer(f"⚠️ Ошибка: {e}", show_alert=True)

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
        "- Просмотр товаров (/products)\n"
        "- Фильтр по категориям (/categories)\n"
        "- Управление клиентами\n"
        "- Добавление товаров\n\n"
        "Версия: 1.1"
    )
    await callback.message.edit_text(text, reply_markup=main_menu())
    await callback.answer()


@dp.callback_query(F.data == "add_product")
async def add_product_start(callback: types.CallbackQuery):
    await callback.message.answer("Введите название нового товара:")
    await callback.answer()


# ========== ЗАПУСК БОТА ==========
async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("Вебхук успешно удален")
    except TelegramNetworkError as e:
        print(f"Ошибка при удалении вебхука: {e}")
        exit(1)

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