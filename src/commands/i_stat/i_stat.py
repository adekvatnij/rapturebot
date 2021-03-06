import re
from collections import Counter
from typing import Dict, Optional, List, Tuple

import pytils
import telegram

from src.models.user import User
from src.models.user_stat import UserStat as ModelUserStat

re_personal_pronouns = re.compile(r"\b(я|меня|мне|мной|мною)\b", re.IGNORECASE)


def sum_count(common: List[Tuple[str, int]]) -> int:
    return sum(count for _, count in common)


def parse_pronouns(text: str, anticheat: bool = False) -> List[Tuple[str, int]]:
    words = re_personal_pronouns.findall(text.lower())
    if not words:
        return []
    c = Counter(words)
    common: List[Tuple[str, int]] = c.most_common()
    if anticheat and sum_count(common) > 5:
        common = [(word, 1) for word, count in common]
    return common


def is_foreign_forward(message: telegram.Message, from_uid: Optional[int] = None) -> bool:
    if from_uid is None:
        from_uid = message.from_user.id
    if message.forward_date is not None:
        if message.forward_from is None or message.forward_from.id != from_uid:
            return True
    return False


def get_users_msg_stats(stats: List[Tuple[ModelUserStat, User]], users_i_count: Dict[int, int], all_key) -> list:
    def get_stat(all_count_limit: int) -> list:
        result_ = []
        for user_stat, user in stats:
            i_count = users_i_count.get(user.uid, 0)
            if i_count == 0:
                continue
            all_count = getattr(user_stat, all_key, 0)
            if all_count < all_count_limit:
                continue
            i_percent = i_count / all_count * 100
            result_.append({
                'uid': user.uid,
                'all': all_count,
                'i_count': i_count,
                'i_percent': i_percent
            })
        return result_
    result = get_stat(30)
    if not result:
        result = get_stat(1)
    return sorted(result, key=lambda x: x['i_percent'], reverse=True)[:15]


class ChatStatistician(object):
    def __init__(self):
        self.db = ChatStat()

    def add_message(self, message: telegram.Message) -> int:
        if is_foreign_forward(message):
            return 0

        text = message.text if message.text else message.caption
        if text is None:
            return 0

        user_id = message.from_user.id
        counts = parse_pronouns(text, anticheat=True)
        if counts:
            self.db.add_message(user_id)
        for word, count in counts:
            self.db.add_word(user_id, word, count)
        return sum_count(counts)

    def reset(self, user_id: int) -> None:
        self.db.reset(user_id)

    def show_personal_stat(self, user_id: int) -> str:
        def fun_word(word: str, fem: bool) -> str:
            if word == 'я':
                fem_a = 'а' if user.female else ''
                return f'я сосал{fem_a}'
            if word == 'меня':
                return 'меня ебали'
            if word == 'мне':
                return 'мне похуй'
            if word == 'мной':
                return 'мной восторгаются'
            if word == 'мною':
                return 'мною пренебрегают'
            return word
        
        user = User.get(user_id)
        if not user:
            raise Exception('User SHOULD be exist')

        stat = self.db.users.get(user_id, UserStat())

        fem_a = 'а' if user.female else ''
        all_count = pytils.numeral.get_plural(stat.all_count, 'раз, раза, раз')
        msg_count = pytils.numeral.get_plural(getattr(stat, 'messages_count', 0), 'сообщении, сообщениях, сообщениях')
        header = f'{user.get_username_or_link()} говорил{fem_a} о себе {all_count} в {msg_count}.'

        c = Counter(stat.counts)
        body = '\n'.join((f'<b>{count}.</b> {fun_word(word, user.female)}' for word, count in c.most_common() if count > 0))

        return f'{header}\n\n{body}'.strip()

    def show_chat_stat(self, chat_stats: List[Tuple[ModelUserStat, User]]) -> str:
        def get_all_words() -> str:
            c = Counter(self.db.all.counts)
            return '\n'.join((f'<b>{count}.</b> {word}' for word, count in c.most_common() if count > 0))

        def get_users() -> str:
            def format_user_row(row) -> str:
                user = User.get(row['uid'])
                fullname = row['uid'] if not user else user.fullname
                return f"<b>{row['i_percent']:.0f} %. {fullname}</b> — {row['i_count']} из {row['all']}"

            users_i_msg_count = {uid: stat.messages_count for uid, stat in self.db.users.items()}
            users_i_all_count = {uid: stat.all_count for uid, stat in self.db.users.items()}
            by_messages = get_users_msg_stats(chat_stats, users_i_msg_count, 'text_messages_count')
            by_words = get_users_msg_stats(chat_stats, users_i_all_count, 'words_count')

            by_messages_str = '\n'.join(format_user_row(row) for row in by_messages)
            by_words_str = '\n'.join(format_user_row(row) for row in by_words)
            return f'По сообщениям:\n{by_messages_str}\n\nПо словам:\n{by_words_str}'

        all_count = self.db.all.all_count
        users = get_users()
        words = get_all_words()
        return f'Больше всего о себе говорили:\n\n{users}\n\nСлова ({all_count}):\n{words}'.strip()


class ChatStat(object):
    def __init__(self):
        self.all = UserStat()
        self.users: Dict[int, UserStat] = dict()

    def add_word(self, user_id: int, word: str, count: int) -> None:
        self.all.add_word(word, count)
        self.__add_user(user_id, word, count)

    def add_message(self, user_id: int) -> None:
        self.all.add_message()
        user = self.users.setdefault(user_id, UserStat())
        user.add_message()
        self.users[user_id] = user

    def reset(self, user_id: int) -> None:
        user = self.users.setdefault(user_id, UserStat())

        for word, count in user.counts.items():
            self.all.remove(word, count)

        self.users.pop(user_id, None)

    def __add_user(self, user_id: int, word: str, count: int) -> None:
        user = self.users.setdefault(user_id, UserStat())
        user.add_word(word, count)
        self.users[user_id] = user


class UserStat(object):
    def __init__(self):
        self.all_count = 0
        self.counts: Dict[str, int] = dict()
        self.messages_count = 0

    def add_word(self, word, count=1) -> None:
        current_count = self.counts.get(word, 0)
        self.counts[word] = current_count + count
        self.all_count += count

    def add_message(self) -> None:
        if not hasattr(self, 'messages_count'):
            self.messages_count = 0
        self.messages_count += 1

    def remove(self, word: str, count: int) -> None:
        current_count = self.counts.get(word, 0)
        self.counts[word] = current_count - count
        self.all_count -= count

    def reset(self) -> None:
        self.all_count = 0
        self.counts.clear()
