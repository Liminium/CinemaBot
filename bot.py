import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import AiogramError
from aiogram.types import Message
from aiogram.types import BotCommand
from aiogram.filters import Command
from dotenv import load_dotenv
from aiogram.fsm. context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db import (init_db, add_user, log_query, get_user_history, get_favorites,
                add_to_favorites, remove_from_favorites, get_user_stats)

from request_films import search_movie

load_dotenv()

bot = Bot(token=os.environ['BOT_API'])
dp = Dispatcher()


# Определим состояния
class RemoveFavoriteStates(StatesGroup):
    waiting_for_fav_title = State()


@dp.message(Command("start"))
async def start_cmd(msg: Message):
    await add_user(msg.from_user.id)
    await msg.answer("Привет! Напиши название фильма или сериала, и я найду информацию и ссылки на просмотр 🔍")


@dp.message(Command("help"))
async def help_cmd(msg: Message):
    await msg.answer("👨‍💻 Просто отправь название фильма или сериала, например:\n\n12 cтульев\nВеном\n\nКоманды:\n"
                     "/start — начать\n/help — помощь\n/history — история запросов\n/stats — статистика по фильмам")


@dp.message(Command("history"))
async def history_cmd(msg: Message):
    history = await get_user_history(msg.from_user.id)
    if not history:
        await msg.answer("История пуста.")
        return
    text = "\n".join(f"🔸 {q} → {title}" for q, title in reversed(history[-10:]))
    await msg.answer(f"📜 Последние 10 запросов:\n{text}")


@dp.message(Command('get_favorites'))
async def get_favorites_cmd(msg: Message):
    favorites = await get_favorites(msg.from_user.id)
    if not favorites:
        await msg.answer("Список избранных пуст.")
        return
    text = "\n".join(f"{num + 1}) {film}" for (num, film) in enumerate(favorites[::-1]))
    await msg.answer(f"⭐ Список избранных:\n{text}")


@dp.message(Command('add_favorite'))
async def add_favorites_cmd(msg: Message):
    last = (await get_user_history(msg.from_user.id))[-1][1]
    result = await add_to_favorites(msg.from_user.id, last)
    if result:
        await msg.answer(f"⭐ Фильм «{last}» добавлен в список избранных!")
    else:
        await msg.answer(f"⚠️ Фильм «{last}» уже находится в списке избранных!")



@dp.message(Command("remove_favorite"))
async def ask_fav_title(message: Message, state: FSMContext):
    await message.answer("⌛ Введите название фильма, который хотите удалить из избранного:")
    await state.set_state(RemoveFavoriteStates.waiting_for_fav_title)


@dp.message(RemoveFavoriteStates.waiting_for_fav_title)
async def remove_fav_by_title(message: Message, state: FSMContext):
    user_id = message.from_user.id
    title = message.text.strip()

    removed = await remove_from_favorites(user_id, title)

    if removed:
        await message.answer(f"❌ Фильм «{title}» успешно удалён из избранного.")
    else:
        await message.answer(f"⚠️ Фильм «{title}» не найден в списке избранных.")
    await state.clear()


@dp.message(Command("stats"))
async def stats_cmd(msg: Message):
    stats = await get_user_stats(msg.from_user.id)
    if not stats:
        await msg.answer("Нет статистики.")
        return
    text = "\n".join(f"🎬 {title} — {count} раз" for title, count in stats[:10])
    await msg.answer(f"📊 Твоя статистика:\n{text}")


@dp.message(F.text)
async def movie_search(msg: Message):
    await add_user(msg.from_user.id)
    query = msg.text.strip()

    loading_message = await msg.answer(f'Ищу «{query}»... 🔍')

    result = await search_movie(query)
    if not result:
        await bot.delete_message(msg.chat.id, loading_message.message_id)
        await msg.answer("Ничего не найдено 😔")
        return

    title, year, rating_1, rating_2, poster, desc, links = result

    await log_query(msg.from_user.id, query, title)

    if desc:
        desc = f"\n\n{desc}"
    year = f", {year}"

    text = f"🎬 {title}{year}\n\n⭐️ IMDB: {rating_1}\n⭐ Кинопоиск: {rating_2}{desc}\n\n{links}"

    if len(text) > 1024:  # Если описание слишком большое
        desc = desc[:1021 - len(text)]
        desc += '...'

    text = f"🎬 {title}{year}\n\n⭐️ IMDB: {rating_1}\n⭐ Кинопоиск: {rating_2}{desc}\n\n{links}"

    await bot.delete_message(msg.chat.id, loading_message.message_id)

    try:
        if poster and poster != "N/A":
            await msg.answer_photo(photo=poster, caption=text)
        else:
            await msg.answer(text)
    except AiogramError as e:
        import urllib
        print(e)
        await msg.answer(text)


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="/help", description="❓ Помощь и список команд"),
        BotCommand(command="/start", description="🚀 Начать работу с ботом"),
        BotCommand(command="/history", description="🕘 История запросов"),
        BotCommand(command="/stats", description="📊 Статистика использования"),
        BotCommand(command="/get_favorites", description="⭐ Список избранных"),
        BotCommand(command="/add_favorite", description="➕ Добавить в избранные последний фильм"),
        BotCommand(command="/remove_favorite", description="➖ Удалить из избранных фильм по названию")
    ]
    await bot.set_my_commands(commands)


async def main():
    await init_db()
    await set_bot_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
