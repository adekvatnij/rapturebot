import unittest
from typing import Iterable

from src.commands.ask.ask import Ask

ball_answers = ('Бесспорно', 'Предрешено', 'Никаких сомнений', 'Определённо да', 'Можешь быть уверен в этом',
                'Мне кажется — «да»', 'Вероятнее всего', 'Хорошие перспективы', 'Знаки говорят — «да»', 'Да',
                'Лучше не рассказывать', 'Даже не думай', 'Мой ответ — «нет»', 'По моим данным — «нет»',
                'Перспективы не очень хорошие', 'Весьма сомнительно', 'Нет')


def check(obj: unittest.TestCase, question: str, choices: Iterable[str]) -> None:
    """
    Убеждаемся, что ответ на вопрос состоит только из указанных вариантов ответа
    """
    limit = 1000
    for choice in choices:
        count = 0
        while count < limit:
            count += 1
            answer = Ask.ask(question)
            obj.assertIn(answer, choices)
            if choice == answer:
                break
        else:  # срабатывает если мы дошли до limit, но так и не встретили choice
            obj.fail(f"'{choice}' not found as answer of '{question}'")


class YesNo(unittest.TestCase):
    def test_simple(self):
        check(self, 'бот ты мне ответишь', ball_answers)


class ChoicesViaColon(unittest.TestCase):
    def test_simple(self):
        check(self, 'выбери цвет: зеленый, красный или желтый?', ('зеленый', 'красный', 'желтый'))

    def test_ya(self):
        check(self, 'скажи: я красивый или я умный?', ('ты красивый', 'ты умный'))


class ChoicesViaOr(unittest.TestCase):
    def test_simple(self):
        check(self, 'гадюка или уж?', ('гадюка', 'уж'))
        check(self, 'пойти налево или направо?', ('налево', 'направо'))
        check(self, 'куда мне пойти налево, наверх, прямо или направо?', ('налево', 'направо', 'прямо', 'наверх'))
        check(self, 'мне купить 🐟, 🐸 или 🐍?', ('🐟', '🐸', '🐍'))
        check(self, 'я красавчик или умница?', ('ты красавчик', 'умница'))
        check(self, 'я красавчик или я умница?', ('ты красавчик', 'ты умница'))

    def test_or_not(self):
        check(self, 'мне есть мороженное или нет???', ('да', 'нет'))
