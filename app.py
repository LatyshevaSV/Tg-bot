import asyncio
import aiohttp
import os
import logging
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramNetworkError
from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.orm import Session

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = "7619827644:AAGXHNp-GuSpOcJF5FMNZ7-D3tzvOcMyrsw"
FASHION_API_KEY = os.getenv("FASHION_API_KEY", "mock_api_key")
ITEMS_PER_PAGE = 5
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, timeout=30)
dp = Dispatcher()

# Настройка SQLAlchemy ORM
Base = declarative_base()


# Модель товара
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


# Модель клиента
class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100))
    address = Column(Text)


# Подключение к базе данных
engine = create_engine("sqlite:///./fashion_shop.db", echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


# Функция генерации сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_fashion_trends():
    api_url = "https://6824dee00f0188d7e72b3020.mockapi.io/fashion-trends"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Ошибка API: HTTP {response.status}")
                    return []
    except Exception as e:
        logger.error(f"Ошибка подключения к API: {e}")
        return []


# Главное меню
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛍 Товары", callback_data="products"),
        InlineKeyboardButton(text="👗 Тренды", callback_data="trends")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ О нас", callback_data="about"),
        InlineKeyboardButton(text="📞 Контакты", callback_data="contacts")
    )
    return builder.as_markup()


# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в модный магазин! Выберите раздел:",
        reply_markup=main_menu()
    )


# Обработчик команды /trends
@dp.message(Command("trends"))
async def show_fashion_trends(message: types.Message):
    trends = await get_fashion_trends()
    if not trends:
        await message.answer("⚠️ Не удалось загрузить тренды. Попробуйте позже.")
        return

    items = trends[:ITEMS_PER_PAGE]
    kb_builder = InlineKeyboardBuilder()

    for item in items:
        button_text = f"{item.get('name')} - {item.get('price', 'N/A')}₽"
        kb_builder.button(text=button_text, callback_data=f"trend_{item.get('id')}")

    kb_builder.adjust(1)
    await message.answer("🔥 Актуальные модные тренды:", reply_markup=kb_builder.as_markup())


# Обработчик кнопки "Тренды" из меню
@dp.callback_query(F.data == "trends")
async def trends_callback(callback: types.CallbackQuery):
    await show_fashion_trends(callback.message)
    await callback.answer()


# Обработчик кнопки "Товары" из меню
@dp.callback_query(F.data == "products")
async def products_callback(callback: types.CallbackQuery):
    await callback.message.answer("🛍 Раздел товаров в разработке...")
    await callback.answer()


# Обработчик кнопки "О нас" из меню
@dp.callback_query(F.data == "about")
async def about_callback(callback: types.CallbackQuery):
    await callback.message.answer("ℹ️ Мы - модный магазин с лучшими трендами сезона!")
    await callback.answer()


# Обработчик кнопки "Контакты" из меню
@dp.callback_query(F.data == "contacts")
async def contacts_callback(callback: types.CallbackQuery):
    await callback.message.answer("📞 Наши контакты:\nТелефон: +7 (123) 456-78-90\nEmail: info@fashion-shop.com")
    await callback.answer()


# Обработчик деталей тренда
@dp.callback_query(F.data.startswith("trend_"))
async def trend_detail(callback: types.CallbackQuery):
    trend_id = callback.data.split("_")[1]
    trends = await get_fashion_trends()
    trend = next((item for item in trends if str(item.get("id")) == trend_id), None)

    if trend:
        response = (f"🔥 {trend.get('name', 'Без названия')}\n\n"
                    f"💵 Цена: {trend.get('price', 'N/A')}₽\n"
                    f"📝 Описание: {trend.get('description', 'Нет описания')}\n\n"
                    f"🏷 Категория: {trend.get('category', 'Не указана')}")
        await callback.message.answer(response)
    else:
        await callback.message.answer("Тренд не найден")

    await callback.answer()


# Запуск бота
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())