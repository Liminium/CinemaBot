import aiosqlite
from typing import List, Tuple

DB_NAME = "cinema_bot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                query TEXT,
                result_title TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER,
                title TEXT,
                PRIMARY KEY (user_id, title)
            )
        ''')
        await db.commit()

async def add_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        await db.commit()

async def log_query(user_id: int, query: str, result_title: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT INTO queries (user_id, query, result_title) VALUES (?, ?, ?)',
                         (user_id, query, result_title))
        await db.commit()

async def get_user_history(user_id: int) -> List[Tuple[str, str]]:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('SELECT query, result_title FROM queries WHERE user_id = ?', (user_id,))
        return await cursor.fetchall()

async def get_user_stats(user_id: int) -> List[Tuple[str, int]]:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('''
            SELECT result_title, COUNT(*) FROM queries
            WHERE user_id = ?
            GROUP BY result_title
            ORDER BY COUNT(*) DESC
        ''', (user_id,))
        return await cursor.fetchall()

# ----------- FAVORITES FUNCTIONS -----------

async def add_to_favorites(user_id: int, title: str):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await (await db.execute('SELECT title FROM favorites WHERE user_id = ?', (user_id,))).fetchall()
        rows = [''.join(row[0].split()).lower() for row in cursor]
        if ''.join(title.split()).lower() in rows:
            return False
        await db.execute('INSERT OR IGNORE INTO favorites (user_id, title) VALUES (?, ?)', (user_id, title))
        await db.commit()
        return True

async def remove_from_favorites(user_id: int, title: str):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('SELECT title FROM favorites WHERE user_id = ?', (user_id,))
        rows = [''.join(row[0].split()).lower() for row in (await cursor.fetchall())]
        if ''.join(title.split()).lower() in rows:
            await db.execute('DELETE FROM favorites WHERE user_id = ? AND title = ?', (user_id, title))
            await db.commit()
            return True
        return False


async def get_favorites(user_id: int) -> List[str]:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('SELECT title FROM favorites WHERE user_id = ?', (user_id,))
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
