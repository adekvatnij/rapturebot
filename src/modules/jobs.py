# coding=UTF-8
from datetime import datetime
from time import sleep

import telegram
from telegram.ext import run_async

from src.config import CONFIG, get_config_chats
from src.modules.dayof.day_manager import DayOfManager
from src.modules.models.leave_collector import LeaveCollector
from src.modules.models.reply_top import ReplyDumper
from src.modules.weather import send_alert_if_full_moon
from src.utils.cache import pure_cache, FEW_DAYS


@run_async
def daily_midnight(bot: telegram.Bot, _):
    # особый режим сегодняшнего дня
    DayOfManager.midnight(bot)

    # для каждого чата
    for chat in get_config_chats():
        if 'daily_full_moon_check' in chat.enabled_commands:
            send_alert_if_full_moon(bot, chat.chat_id)
            sleep(0.5)

    for cid in CONFIG["weekly_stats_chats_ids"]:
        ReplyDumper.dump(cid)

@run_async
def daily_afternoon(bot: telegram.Bot, _):
    DayOfManager.afternoon(bot)

def lefts_check(bot: telegram.Bot, _):
    LeaveCollector.check_left_users(bot)

def health_log(*_):
    now = datetime.now()
    pure_cache.append_list(f"health_log:{now.strftime('%Y%m%d')}", now.strftime('%H:%M'), time=FEW_DAYS)
