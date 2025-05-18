import aiohttp
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from typing import Any
import dotenv
import math
import os

dotenv.load_dotenv()


def normalize_string(s: str) -> str:
    """Убирает все символы, не являющиеся строкой или цифрой"""
    return ''.join([i for i in s if i.isalnum()])


def levenstein_distance(user_query: str, response_title: str) -> int:
    """Функция, которая находит максимально близкое название фильма к названию, введенному пользователем"""
    m, n = len(user_query), len(response_title)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if user_query[i - 1] == response_title[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(
                    dp[i - 1][j] + 1,
                    dp[i][j - 1] + 1,
                    dp[i - 1][j - 1] + 1
                )

    return dp[m][n]


async def search_movie(query: str) -> tuple[Any, Any, Any, Any, Any, Any, str] | None:
    async with aiohttp.ClientSession() as session:
        params = {
            "page": 1,
            'query': query,
            'limit': 100
        }
        headers = {
            "accept": "application/json",
            "X-API-KEY": os.environ['KINOPOISK_API']
        }
        async with session.get("https://api.kinopoisk.dev/v1.4/movie/search", params=params, headers=headers) as resp:

            data = await resp.json()

            title = rating_1 = rating_2 = poster = description = None
            min_distance = math.inf

            for film in data['docs']:
                if (new_dist := levenstein_distance(normalize_string("".join(film['name'].split())),
                                                    normalize_string("".join(query.split())))) < min_distance:
                    min_distance = new_dist

                    title = film.get('name', '')
                    if not title:
                        title = film.get('alternativeName', '')
                    year = film.get('year', "")
                    description = film.get('description', '')
                    rating_1 = film.get('rating', {}).get('imdb', '')
                    rating_2 = film.get('rating', {}).get('kp', '')
                    try:
                        poster = film.get('poster', {}).get("url", "")
                    except AttributeError:
                        poster = ""

            if title is not None:  # Хоть что-то было найдено
                if title == '':
                    title = query

                links = await find_watch_links(title, year if year is not None else "")

                return title, year, rating_1, rating_2, poster, description, links


async def find_watch_links(title: str, year: str) -> str:
    query = quote_plus(f"Смотреть онлайн бесплатно {title} {year}")
    url = f"https://www.google.com/search?q={query}&hl=ru&gl=ru&num=10"
    headers = {"User-Agent": f"Lynx/3.8.0 libwww-FM/2.15 SSL-MM/1.4 OpenSSL/1.3.0"}

    links: list[str] = []

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=5) as resp:
                resp.raise_for_status()
                text = await resp.text()

        soup = BeautifulSoup(text, "html.parser")

        for a in soup.find_all("a", class_="fuLhoc ZWRArf", href=True):
            links.append(a['href'].lstrip('/url?q=').split('&')[0])
            if len(links) == 4:
                break

        if not links:
            return 'К сожалению, ссылки не были найдены'
        else:
            return 'Смотреть: \n' + '\n'.join(links)

    except Exception as e:
        print(f"Error during search: {e!r}")
        return 'К сожалению, ссылки не были найдены'