# Импорт необходимых библиотек
import asyncio
import aiohttp
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Настройка бота
bot = Bot(token=("7619827644:AAGXHNp-GuSpOcJF5FMNZ7-D3tzvOcMyrsw"))
dp = Dispatcher()

# Главное меню
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛍 Товары", callback_data="products"),
        InlineKeyboardButton(text="👗 Тренды", callback_data="trends")
    )
    return builder.as_markup()

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать!",
        reply_markup=main_menu()
    )

# Обработчик команды /trends
@dp.message(Command("trends"))
async def cmd_trends(message: types.Message):
    try:
        # Ваш код получения трендов
        await message.answer("Вот текущие тренды...")
    except Exception:
        await message.answer("⚠️ Не удалось загрузить тренды. Попробуйте позже.")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())