"""
Рядовой ночной стражи
"""
import random
from datetime import datetime
from threading import Timer

import pytils
import telegram

from src.config import CONFIG
from src.modules.khaleesi import Khaleesi

CACHE_KEY = 'night_watch'


def go_go_watchmen(bot: telegram.Bot) -> None:
    """
    Стражник смотрит на часы: а пора ли уже идти в дозор?
    """
    # стражник выходит на работу в 22 часа
    if datetime.now().hour != 22:
        return

    # говорим фразу через случайные N часов
    _postpone_our_phrase(bot)


def get_hour(now: datetime) -> str:
    """
    Отсылка к Пратчетту.
    """
    hour = int(now.strftime("%I"))
    plural = pytils.numeral.sum_string(hour, pytils.numeral.MALE, 'час, часа, часов')
    return f'{plural} и все спокойно!'.upper()


def _all_s_well(bot: telegram.Bot) -> None:
    """
    Отправляет в основной чат сообщение типа "12 часов и все спокойно"
    """
    if 'anon_chat_id' not in CONFIG:
        return
    text = f'{Khaleesi.khaleesi(get_hour(datetime.now()))} 🐉'
    bot.send_message(CONFIG['anon_chat_id'], text)


def _postpone_our_phrase(bot: telegram.Bot) -> None:
    """
    Через случайное время запускает функцию `all_s_well`
    """
    wait = _how_long_we_should_wait()
    timer = Timer(wait, _all_s_well, args=[bot])
    timer.start()


def _how_long_we_should_wait() -> int:
    """
    Возвращает случайно от 1 до 6 часов в секундах
    """
    hour = 60 * 60
    wait = random.randint(1 * hour, 6 * hour)
    return wait
