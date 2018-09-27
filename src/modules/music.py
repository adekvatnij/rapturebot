# coding=UTF-8

from functools import wraps
from typing import List, Set, Tuple, Iterable

import telegram

from src.modules.models.chat_user import ChatUser
from src.modules.models.user import User
from src.utils.cache import cache, YEAR
from src.utils.handlers_helpers import check_admin

CACHE_KEY = 'music'


def only_who_can_manage_music_users(f):
    @wraps(f)
    def decorator(bot: telegram.Bot, update: telegram.Update):
        message = update.message
        if not can_manage_music_users(bot, message.chat_id, message.from_user.id):
            bot.send_message(message.chat_id, 'Только админы чата и членессы музкружка могут делать это',
                             reply_to_message_id=message.message_id)
            return
        return f(bot, update)
    return decorator


def can_manage_music_users(bot: telegram.Bot, chat_id: int, uid: int) -> bool:
    if check_admin(bot, chat_id, uid):
        return True
    if is_music_user(chat_id, uid):
        return True
    return False


def get_music_users(chat_id: int) -> Set[int]:
    return set(cache.get(f'{CACHE_KEY}:{chat_id}:uids', []))


def set_music_users(chat_id: int, uids: Iterable[int]) -> None:
    cache.set(f'{CACHE_KEY}:{chat_id}:uids', set(uids), time=YEAR)


def is_music_user(chat_id: int, uid: int) -> bool:
    return uid in get_music_users(chat_id)


def get_args(text: str) -> List[str]:
    words = text.strip().split()
    if len(words) >= 2:
        return words[1:]
    return []


def find_users(message: telegram.Message, usernames: List[str]) -> Tuple[List[str], Set[int], List[str]]:
    not_found_usernames: List[str] = []
    found_uids: Set[int] = set()
    found_usernames: List[str] = []

    for username in usernames:
        uid = User.get_id_by_name(username)
        if uid is None:
            # на случай если вместо юзернейма указан цифровой user_id
            uid = User.get(username)
        if uid is None:
            not_found_usernames.append(username)
            continue
        found_uids.add(uid)
        found_usernames.append(username.lstrip('@'))

    # ищем упоминания людей без юзернейма
    for entity, entity_text in message.parse_entities().items():
        if entity.type == 'text_mention':
            uid = entity.user.id
            user = User.get(uid)
            if user is None:
                continue
            found_uids.add(uid)
            found_usernames.append(user.fullname)

    return not_found_usernames, found_uids, found_usernames


def get_manage_users_text(action: str, not_found_usernames, found_usernames) -> str:
    text = ''
    if len(found_usernames) > 0:
        text = f'{action}: {", ".join(found_usernames)}'
    if len(not_found_usernames) > 0:
        text += f'\n\nНе найдены: {", ".join(not_found_usernames)}'
    if len(text) == 0:
        text = 'Ошибка'
    return text.strip()


def add_users(bot: telegram.Bot, message: telegram.Message, usernames: List[str]) -> None:
    not_found_usernames, found_uids, found_usernames = find_users(message, usernames)
    chat_id = message.chat_id
    if len(found_uids) > 0:
        music_uids = get_music_users(chat_id)
        music_uids.update(found_uids)
        set_music_users(chat_id, music_uids)
    text = get_manage_users_text('Добавлены', not_found_usernames, found_usernames)
    bot.send_message(chat_id, text, reply_to_message_id=message.message_id)


def del_users(bot: telegram.Bot, message: telegram.Message, usernames: List[str]) -> None:
    not_found_usernames, found_uids, found_usernames = find_users(message, usernames)
    chat_id = message.chat_id
    if len(found_uids) > 0:
        music_uids = get_music_users(chat_id)
        music_uids = music_uids - found_uids
        set_music_users(chat_id, music_uids)
    text = get_manage_users_text('Удалены', not_found_usernames, found_usernames)
    bot.send_message(chat_id, text, reply_to_message_id=message.message_id)


def format_users(chat_id: int, uids: Iterable[int]) -> List[str]:
    users = []
    chat_uids: Set[int] = set([chat_user.uid for chat_user in ChatUser.get_all(chat_id)])
    for uid in uids:
        user = User.get(uid)
        # если юзера нет в базе, то добавляем его uid, чтобы хотя бы так можно было удалить
        if user is None:
            users.append(uid)
            continue
        # если юзера нет в чате, то добавляем его с тегом
        if uid not in chat_uids:
            users.append(user.get_username_or_link())
            continue
        # если нет юзернейма, указыаем uid
        if user.username is None:
            users.append(f'{user.fullname} ({user.uid})')
            continue
        # для остальных добавляем юзернейм без тега
        users.append(user.username.lstrip('@'))
    return users


def format_chat_users(chat_id: int, uids: Iterable[int]) -> List[str]:
    users = []
    chat_uids: Set[int] = set([chat_user.uid for chat_user in ChatUser.get_all(chat_id)])
    for uid in uids:
        user = User.get(uid)
        if user is None:
            continue
        if uid not in chat_uids:
            continue
        users.append(user.get_username_or_link())
    return users


def send_list_replay(bot: telegram.Bot, chat_id: int, message_id: int, uids: Iterable[int]) -> None:
    formatted_chat_users = format_chat_users(chat_id, uids)
    text = f'#музкружок {" ".join(formatted_chat_users)}'
    bot.send_message(chat_id, text, reply_to_message_id=message_id, parse_mode='HTML')


def send_sorry(bot: telegram.Bot, chat_id: int, message_id: int) -> None:
    bot.send_message(chat_id, 'Для этого тебе нужно быть в музкружке', reply_to_message_id=message_id)


def music(bot: telegram.Bot, update: telegram.Update) -> None:
    chat_id = update.message.chat_id
    message: telegram.Message = update.message
    music_users = get_music_users(chat_id)
    can_use = message.from_user.id in music_users

    # команда с текстом
    # бот делает реплай к этому сообщению, независимо от того, есть ли у сообщения реплай или нет.
    if len(get_args(message.text.strip())) > 0:
        if can_use:
            send_list_replay(bot, chat_id, message.message_id, music_users)
            return
        send_sorry(bot, chat_id, message.message_id)
        return

    # команда без текста, но с реплаем
    if message.reply_to_message is not None:
        if can_use:
            send_list_replay(bot, chat_id, message.reply_to_message.message_id, music_users)
            return
        send_sorry(bot, chat_id, message.message_id)
        return

    # без текста, без реплая
    help = 'Команда для музкружка. Использование: \n\n• /music текст — бот делает реплай сообщения с тегами музкружка.\n• /music (без текста, но с реплаем) — бот делает реплай к реплаю.\n\nАдмины чата и люди музкружка могут добавлять и удалять участников при помощи команд /musicadd и /musicdel.'
    formatted_users = format_users(chat_id, music_users)
    bot.send_message(chat_id, f'{help}\n\nЛюди музкружка ({len(formatted_users)}): {", ".join(formatted_users)}', reply_to_message_id=message.message_id, parse_mode='HTML')


@only_who_can_manage_music_users
def musicadd(bot: telegram.Bot, update: telegram.Update) -> None:
    """
    Добавляет участника в музкружок. Работает только у админов чата и участников музкружка.
    Пример:
        /musicadd @username1 username2
    """
    message = update.message
    args = get_args(message.text)
    if len(args) > 0:
        add_users(bot, message, args)


@only_who_can_manage_music_users
def musicdel(bot: telegram.Bot, update: telegram.Update) -> None:
    message = update.message
    args = get_args(message.text)
    if len(args) > 0:
        del_users(bot, message, args)
