import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiohttp import web
from database import init_db, log_event, get_daily_stats

# Вставьте ваш токен бота ниже
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8545729872:AAHXSSq2C9dfkcTN7Yr7zVM8yTmFGOWlwOg")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализируем базу данных при запуске
init_db()

# Вспомогательная функция проверки прав администратора
async def is_user_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("creator", "administrator")
    except Exception:
        return True

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Бот для отслеживания голосовых чатов запущен!")

# Команда статистики с обнулением в 00:00 МСК
@dp.message(Command("day_stats"))
async def cmd_day_stats(message: Message):
    stats = get_daily_stats(message.chat.id)
    if not stats:
        text = (
            "📊 **Статистика голосовых чатов за сегодня (с обнулением в 00:00 МСК):**\n\n"
            "За сегодня активности в голосовых чатах не зафиксировано."
        )
        await message.answer(text, parse_mode="Markdown")
        return
    
    text = "📊 **Статистика голосовых чатов за сегодня (с обнулением в 00:00 МСК):**\n\n"
    for idx, (user_label, started, ended, duration) in enumerate(stats, 1):
        mins = duration // 60
        username = f"@{user_label}" if not user_label.startswith("@") else user_label
        text += f"{idx}. **{username}**\n"
        text += f"   • Запустил(а): {started} раз(а)\n"
        text += f"   • Завершил(а): {ended} раз(а)\n"
        text += f"   • Общее время: {mins} мин\n\n"
    
    await message.answer(text, parse_mode="Markdown")

# Запуск голосового чата — отправляем кнопку для организатора
@dp.message(F.video_chat_started)
async def voice_chat_started(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✋ Я организатор (отметиться)", callback_data="claim_start")]
    ])
    await message.answer(
        "🎙 **Голосовой чат запущен!**\nОрганизатор (администратор), нажмите кнопку ниже, чтобы зафиксировать за собой запуск:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "claim_start")
async def process_claim_start(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user = callback.from_user
    
    # Проверка на админа
    if not await is_user_admin(chat_id, user.id):
        await callback.answer("⛔ Эта кнопка только для администраторов!", show_alert=True)
        return

    user_label = user.username or user.first_name
    log_event(chat_id, user.id, user_label, 'started', 0)
    await callback.message.edit_text(f"🎙 Голосовой чат запустил(а):\n@{user_label}")
    await callback.answer()

# Завершение голосового чата — универсальная обработка события
@dp.message(F.video_chat_ended | F.content_type.in_({"video_chat_ended", "voice_chat_ended"}))
async def voice_chat_ended(message: Message):
    chat_ended_data = getattr(message, 'video_chat_ended', None) or getattr(message, 'voice_chat_ended', None)
    duration = chat_ended_data.duration if chat_ended_data else 0
    
    mins = duration // 60
    secs = duration % 60
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏁 Я завершил(а) ГЧ (отметить)", callback_data=f"claim_end_{duration}")]
    ])
    await message.answer(
        f"🏁 **Голосовой чат завершен.**\nДлительность: {mins} мин {secs} сек.\n\nКто завершил чат? Нажмите кнопку ниже:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("claim_end_"))
async def process_claim_end(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user = callback.from_user
    
    # Проверка на админа
    if not await is_user_admin(chat_id, user.id):
        await callback.answer("⛔ Эта кнопка только для администраторов!", show_alert=True)
        return

    duration = int(callback.data.split("_")[2])
    user_label = user.username or user.first_name
    log_event(chat_id, user.id, user_label, 'ended', duration)
    
    mins = duration // 60
    secs = duration % 60
    await callback.message.edit_text(
        f"🏁 Голосовой чат завершил(а):\n@{user_label}\n⏱ Длительность: {mins} мин {secs} сек"
    )
    await callback.answer()

# Веб-сервер для поддержания активности на Render
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
