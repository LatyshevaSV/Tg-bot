import sqlite3
import asyncio
import aiohttp
import os
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramNetworkError
from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

# Настройка логирования
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("7619827644:AAGXHNp-GuSpOcJF5FMNZ7-D3tzvOcMyrsw")
FASHION_API_KEY = os.getenv("FASHION_API_KEY", "mock_api_key")  # Для тестов
ITEMS_PER_PAGE = 5
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Настройки сервера
LOCAL_SERVER_HOST = "0.0.0.0"  # Подключения со всех интерфейсов
LOCAL_SERVER_PORT = 8080
WEBHOOK_PATH = "/webhook"
BASE_WEBHOOK_URL = f"http://localhost:{LOCAL_SERVER_PORT}"  # Для локального тестирования

# Инициализация бота
bot = Bot(token=BOT_TOKEN, timeout=30)
dp = Dispatcher()

# Настройка SQLAlchemy ORM
Base = declarative_base()


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    category = Column(String(50))
    description = Column(Text)
    image_path = Column(String(255))
    size = Column(String(20))
    color = Column(String(30))


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100))
    address = Column(Text)


# Подключение к БД
engine = create_engine("sqlite:///./fashion_shop.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# API для модных трендов
async def get_fashion_trends():
    """Получает тренды из MockAPI"""
    api_url = "https://6824dee00f0188d7e72b3020.mockapi.io/fashion-trends"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Ошибка API: {response.status}")
                return []
    except Exception as e:
        logger.error(f"Ошибка подключения к API: {e}")
        return []


# Клавиатуры
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛍 Товары", callback_data="products"),
        InlineKeyboardButton(text="👗 Тренды", callback_data="trends")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Клиенты", callback_data="clients"),
        InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")
    )
    return builder.as_markup()


# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в магазин модной одежды!\n"
        "Используйте меню для навигации:",
        reply_markup=main_menu()
    )


@dp.message(Command("trends"))
async def cmd_trends(message: types.Message):
    """Показывает текущие тренды из MockAPI"""
    trends = await get_fashion_trends()

    if not trends:
        await message.answer("⚠️ Не удалось загрузить тренды. Попробуйте позже.")
        return

    response = "👗 Актуальные тренды:\n\n" + "\n".join(
        f"• <b>{trend['name']}</b>\n{trend['description']}\n"
        for trend in trends[:2]
    )

    await message.answer(response, parse_mode="HTML")


@dp.message(Command("products"))
async def cmd_products(message: types.Message):
    db = next(get_db())
    products = db.query(Product).limit(ITEMS_PER_PAGE).all()
    if products:
        response = "📦 Товары:\n\n" + "\n".join(
            f"{p.id}. {p.name} - {p.price}₽ ({p.size}, {p.color})" for p in products
        )
    else:
        response = "🛒 Товаров пока нет"
    await message.answer(response)


@dp.message(F.photo)
async def handle_product_photo(message: types.Message):
    db = next(get_db())
    photo = message.photo[-1]
    file_id = photo.file_id
    file = await bot.get_file(file_id)
    file_path = UPLOAD_DIR / f"{file_id}.jpg"

    await bot.download_file(file.file_path, destination=file_path)

    new_product = Product(
        name="Новый товар",
        price=0,
        category="Одежда",
        image_path=str(file_path),
        size="M",
        color="Черный"
    )
    db.add(new_product)
    db.commit()
    await message.answer(f"📸 Товар добавлен! ID: {new_product.id}")


# Дополнительные API поинты
async def health_check(request):
    """Проверка работоспособности сервера"""
    return web.Response(text="Сервер работает!")


async def get_products_api(request):
    """API для получения товаров"""
    db = next(get_db())
    products = db.query(Product).all()
    products_data = [{
        "id": p.id,
        "name": p.name,
        "price": p.price,
        "category": p.category
    } for p in products]
    return web.json_response(products_data)


async def on_startup(bot: Bot):
    """Настройка вебхука при запуске"""
    await bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}")


async def start_local_server():
    """Запуск локального сервера"""
    await on_startup(bot)

    app = web.Application()
    # Регистрация обработчиков
    SimpleRequestHandler(dp, bot).register(app, path=WEBHOOK_PATH)
    app.router.add_get("/", health_check)
    app.router.add_get("/api/products", get_products_api)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=LOCAL_SERVER_HOST, port=LOCAL_SERVER_PORT)

    logger.info(f"Сервер запущен на http://{LOCAL_SERVER_HOST}:{LOCAL_SERVER_PORT}")
    logger.info(f"Вебхук: {BASE_WEBHOOK_URL}{WEBHOOK_PATH}")

    await site.start()

    # Бесконечное ожидание
    await asyncio.Event().wait()


async def start_polling():
    """Запуск в режиме polling"""
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def main():
    """Основная функция запуска"""
    try:
        # Для локального тестирования с сервером
        await start_local_server()


    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
