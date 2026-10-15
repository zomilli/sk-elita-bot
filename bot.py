import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiohttp import web
from database import (
    init_db, log_event, get_daily_stats, 
    get_user_total_stats, give_achievement, get_user_achievements
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8545729872:AAEL4BGFH6MwKDNpLAvhudfQsIhZhln0nEw")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализируем базу данных при запуске
init_db()

# Список всех доступных ачивок с крутыми названиями (без зачеркиваний)
ACHIEVEMENTS_LIST = {
    "first_gc": {"title": "🎙 Раскочегарил микро", "desc": "Провести свой самый первый ГЧ"},
    "1h_gc": {"title": "⚡ Час пик", "desc": "Провести ГЧ длительностью более 1 часа"},
    "3h_gc": {"title": "🔥 Железный купол", "desc": "Провести ГЧ длительностью более 3 часов"},
    "night_owl": {"title": "🦇 Ночной дозор", "desc": "Завершить ГЧ в период с 00:00 до 05:00 МСК"},
    "10_gcs": {"title": "🎯 Легенда эфира", "desc": "Суммарно провести 10 голосовых чатов"},
    "24h_total": {"title": "👑 Бессменный лидер", "desc": "Набрать в сумме 24 часа проведённых ГЧ"},
}

# Вспомогательная функция проверки прав администратора
async def is_user_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("creator", "administrator")
    except Exception:
        return True

# Функция проверки и выдачи ачивок
async def check_and_grant_achievements(message: Message, user_id: int, user_label: str, last_duration: int = 0):
    chat_id = message.chat.id
    total_started, total_ended, total_duration = get_user_total_stats(chat_id, user_id)
    
    unlocked = []

    # 1. Первый ГЧ
    if total_started >= 1 or total_ended >= 1:
        if give_achievement(chat_id, user_id, "first_gc"):
            unlocked.append(ACHIEVEMENTS_LIST["first_gc"])

    # 2. Длительность одного ГЧ > 1 часа (3600 сек)
    if last_duration >= 3600:
        if give_achievement(chat_id, user_id, "1h_gc"):
            unlocked.append(ACHIEVEMENTS_LIST["1h_gc"])

    # 3. Длительность одного ГЧ > 3 часов (10800 сек)
    if last_duration >= 10800:
        if give_achievement(chat_id, user_id, "3h_gc"):
            unlocked.append(ACHIEVEMENTS_LIST["3h_gc"])

    # 4. Ночная сова (с 00:00 до 05:00 МСК)
    current_hour = (datetime.utcnow().hour + 3) % 24
    if 0 <= current_hour < 5:
        if give_achievement(chat_id, user_id, "night_owl"):
            unlocked.append(ACHIEVEMENTS_LIST["night_owl"])

    # 5. 10 проведённых ГЧ
    if (total_started + total_ended) >= 10:
        if give_achievement(chat_id, user_id, "10_gcs"):
            unlocked.append(ACHIEVEMENTS_LIST["10_gcs"])

    # 6. Суммарно 24 часа в ГЧ (86400 сек)
    if total_duration >= 86400:
        if give_achievement(chat_id, user_id, "24h_total"):
            unlocked.append(ACHIEVEMENTS_LIST["24h_total"])

    # Отправляем сообщение, если получена новая ачивка
    for ach in unlocked:
        text = (
            f"🎉 **ПОЗДРАВЛЯЕМ!** 🎉\n"
            f"Пользователь @{user_label} разблокировал(а) новое достижение:\n\n"
            f"🏆 **{ach['title']}**\n"
            f"ℹ️ *{ach['desc']}*"
        )
        await message.answer(text, parse_mode="Markdown")

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Бот для отслеживания голосовых чатов и ачивок запущен!")

# Универсальная команда статистики с исправленным выводом при отсутствии данных
@dp.message(F.text.lower().startswith("/day_stats") | F.text.lower().in_({"статистика", "стат"}))
async def cmd_day_stats(message: Message):
    stats = get_daily_stats(message.chat.id)
    if not stats:
        await message.answer(
            "📊 **Статистика голосовых чатов за сегодня (с обнулением в 00:00 МСК):**\n\n"
            "За сегодня активности в голосовых чатах не зафиксировано.",
            parse_mode="Markdown"
        )
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

# Команда просмотра ачивок
@dp.message(Command("achievements", "my_achievements"))
async def cmd_achievements(message: Message):
    user = message.from_user
    user_label = user.username or user.first_name
    unlocked_codes = get_user_achievements(message.chat.id, user.id)
    
    text = f"🏆 **Достижения пользователя @{user_label}:**\n\n"
    for code, info in ACHIEVEMENTS_LIST.items():
        if code in unlocked_codes:
            text += f"✅ **{info['title']}** — {info['desc']}\n"
        else:
            text += f"🔒 _{info['title']}_ — {info['desc']}\n"
            
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
    
    if not await is_user_admin(chat_id, user.id):
        await callback.answer("⛔ Эта кнопка только для администраторов!", show_alert=True)
        return

    user_label =
