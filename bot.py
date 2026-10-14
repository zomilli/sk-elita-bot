import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiohttp import web
from database import init_db, log_event, get_daily_stats

# Токен вашего бота
BOT_TOKEN = "8545729872:AAEL4BGFH6MwKDNpLAvhudfQsIhZhln0nEw"  # <--- Вставьте сюда ваш токен!

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация БД
init_db()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Бот для отслеживания голосовых чатов запущен!")

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    stats = get_daily_stats(message.chat.id)
    if not stats:
        await message.answer("За сегодня активности в голосовых чатах не зафиксировано.")
        return
    
    text = "📊 **Статистика голосовых чатов за сегодня:**\n\n"
    for user_label, started, ended, duration in stats:
        mins = duration // 60
        text += f"👤 **{user_label}**: {mins} мин. (Запусков: {started}, Завершений: {ended})\n"
    
    await message.answer(text, parse_mode="Markdown")

# Заглушка веб-сервера для Render (чтобы он видел открытый порт)
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render передает порт через переменную PORT, по умолчанию 10000
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    # Запускаем мини-веб-сервер
    await start_web_server()
    # Запускаем самого бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
