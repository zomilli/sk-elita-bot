import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.session.aiohttp import AiohttpSession

from database import init_db, log_event, get_weekly_stats

# ВСТАВЬ СЮДА СВОЙ ТОКЕН НИЖЕ
TOKEN = "8545729872:AAEL4BGFH6MwKDNpLAvhudfQsIhZhln0nEw"

# Настройка бесплатного прокси PythonAnywhere
session = AiohttpSession(proxy="http://proxy.server:3128")
bot = Bot(token=TOKEN, session=session)
dp = Dispatcher()

# Временное хранилище длительности для кнопок завершения
ended_chats_duration = {}


# --- СТАРТ ГЧ ---
@dp.message(F.video_chat_started)
async def on_voice_started(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✋ Я организатор (отметиться)", 
                    callback_data="claim_organizer"
                )
            ]
        ]
    )
    
    await message.reply(
        "🎙 <b>Голосовой чат запущен!</b>\n"
        "Организатор, нажмите кнопку ниже, чтобы зафиксировать за собой запуск:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data == "claim_organizer")
async def on_claim_organizer(callback: types.CallbackQuery):
    member = await callback.bot.get_chat_member(callback.message.chat.id, callback.from_user.id)
    if member.status not in ["creator", "administrator"]:
        await callback.answer("❌ Нажимать эту кнопку могут только администраторы!", show_alert=True)
        return

    user = callback.from_user
    label = f"@{user.username}" if user.username else user.first_name
    
    log_event(callback.message.chat.id, user.id, label, "started")
    
    await callback.message.edit_text(
        f"🎙 Голосовой чат запустил(а): <b>{label}</b>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer("Успешно! Вы отмечены как организатор.")


# --- ЗАВЕРШЕНИЕ ГЧ ---
@dp.message(F.video_chat_ended)
async def on_voice_ended(message: types.Message):
    duration_sec = message.video_chat_ended.duration
    
    # Сохраняем длительность для этого сообщения
    ended_chats_duration[message.message_id] = duration_sec

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏁 Я завершил(а) ГЧ (отметиться)", 
                    callback_data=f"claim_ender:{message.message_id}"
                )
            ]
        ]
    )

    hours = duration_sec // 3600
    minutes = (duration_sec % 3600) // 60
    seconds = duration_sec % 60
    time_str = f"{hours} ч " if hours > 0 else ""
    time_str += f"{minutes} мин {seconds} сек"

    await message.reply(
        f"🏁 <b>Голосовой чат завершен.</b>\n"
        f"⏱ Длительность: <b>{time_str}</b>\n\n"
        f"Кто завершил чат? Нажмите кнопку ниже:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("claim_ender:"))
async def on_claim_ender(callback: types.CallbackQuery):
    member = await callback.bot.get_chat_member(callback.message.chat.id, callback.from_user.id)
    if member.status not in ["creator", "administrator"]:
        await callback.answer("❌ Нажимать эту кнопку могут только администраторы!", show_alert=True)
        return

    user = callback.from_user
    label = f"@{user.username}" if user.username else user.first_name
    
    msg_id = int(callback.data.split(":")[1])
    duration_sec = ended_chats_duration.get(msg_id, 0)

    log_event(callback.message.chat.id, user.id, label, "ended", duration_sec)

    hours = duration_sec // 3600
    minutes = (duration_sec % 3600) // 60
    seconds = duration_sec % 60
    time_str = f"{hours} ч " if hours > 0 else ""
    time_str += f"{minutes} мин {seconds} сек"

    await callback.message.edit_text(
        f"🏁 Голосовой чат завершил(а): <b>{label}</b>\n"
        f"⏱ Длительность: <b>{time_str}</b>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer("Успешно! Вы отмечены как завершивший.")


# --- СТАТИСТИКА ---
@dp.message(Command("week_stats"))
async def cmd_week_stats(message: types.Message):
    stats = get_weekly_stats(message.chat.id)
    if not stats:
        await message.answer("📊 За последние 7 дней активности не зафиксировано.")
        return

    text = "📊 <b>Статистика голосовых чатов за неделю:</b>\n\n"
    for idx, row in enumerate(stats, 1):
        user_label, started, ended, total_sec = row
        hours = total_sec // 3600
        minutes = (total_sec % 3600) // 60
        time_formatted = f"{hours} ч {minutes} мин" if hours > 0 else f"{minutes} мин"
            
        text += (
            f"{idx}. {user_label}\n"
            f"   • Запустил(а): <b>{started}</b> раз(а)\n"
            f"   • Завершил(а): <b>{ended}</b> раз(а)\n"
            f"   • Общее время: <b>{time_formatted}</b>\n\n"
        )

    await message.answer(text, parse_mode=ParseMode.HTML)


async def main():
    init_db()
    # Сброс вебхука перед поллингом
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())