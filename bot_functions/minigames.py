#! /usr/bin/env python
# -*- coding: utf-8 -*-
# dependencies: [telegram_bot]

"""
Модуль для работы с мини-играми (орел или решка, камень ножницы бумага и прочая лабуда)
"""

import sqlite3
import random
import toml
import logging
import sys
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards_telegram.create_keyboards import payload_to_callback

# init
logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)

try:
    config = toml.load('configuration.toml')
except FileNotFoundError:
    logger.critical('configuration.toml не найден!')
    sys.exit()

path = config.get('Kiberded').get('path')  # необходимо для корректной работы на сервере
token = config.get('Kiberded').get('token_telegram')
tg_deeplink_token = config.get('Kiberded').get('deeplink_token_key')
days = [['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'], [' (чёт)', ' (нечёт)']]
timetable = config.get('Kiberded').get('timetable')
admin_chat = config.get('Kiberded').get('telegram_admin_chat')
books_chat = config.get('Kiberded').get('telegram_books_chat')
dayofdaypics_chat = config.get('Kiberded').get('telegram_dayofdaypics_chat')


# /init


def get_coin_flip_result(user_id):
    """
    Функция для получения результата орла или решки
    :return: "Орел" или "Решка"
    """
    result = "Орел" if random.randint(0, 1) else "Решка"
    stats = add_coin_flip_result(user_id, result)
    result += '.\n\n' + stats
    return result


def add_coin_flip_result(user_id, result):
    """
    Функция для добавления результата в базу данных
    :param user_id: id пользователя
    :param result: "Орел" или "Решка"
    :return: Суммарное количество орлов и решек пользователя и общее количество орлов и решек всех юзеров
    """
    with sqlite3.connect(f'{path}admindb/databases/minigames.db') as con:
        cursor = con.cursor()
        now = datetime.now()
        cursor.execute("CREATE TABLE IF NOT EXISTS coin_flip_history (user_id INTEGER, result TEXT, date TEXT)")
        cursor.execute("INSERT INTO coin_flip_history VALUES (?, ?, ?)", (user_id, result, str(now)))
        con.commit()
        # heads - орел, если что
        cursor.execute("CREATE TABLE IF NOT EXISTS coin_flip_stat (user_id INTEGER, heads INTEGER, tails INTEGER)")
        cursor.execute("SELECT * FROM coin_flip_stat WHERE user_id = ?", (user_id,))
        if cursor.fetchone() is None:
            cursor.execute("INSERT INTO coin_flip_stat VALUES (?, ?, ?)", (user_id, 0, 0))
        if result == "Орел":
            cursor.execute("UPDATE coin_flip_stat SET heads = heads + 1 WHERE user_id = ?", (user_id,))
        else:
            cursor.execute("UPDATE coin_flip_stat SET tails = tails + 1 WHERE user_id = ?", (user_id,))

        cursor.execute("SELECT * FROM coin_flip_stat")
        all_heads = 0
        all_tails = 0
        for row in cursor.fetchall():
            all_heads += row[1]
            all_tails += row[2]
        cursor.execute("SELECT * FROM coin_flip_stat WHERE user_id = ?", (user_id,))
        con.commit()
        user_data = cursor.fetchone()
        user_heads = user_data[1]
        user_tails = user_data[2]

        return f'За все время орел выпал в {round((all_heads / (all_heads + all_tails)) * 100)}% случаев из ' \
               f'{all_heads + all_tails} бросков\nУ тебя - в {round((user_heads / (user_heads + user_tails)) * 100)}% ' \
               f'случаев из {user_heads + user_tails} бросков.'


def start_classical_rock_paper_scissors(user_id, date):
    """
    Функция для начала игры в обычный камень-ножницы-бумага с ботом
    :param user_id: id пользователя
    :param date: время старта
    :return: markup
    """
    with sqlite3.connect(f'{path}admindb/databases/minigames.db') as con:
        cursor = con.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS rock_paper_scissors_classical_history"
                       " (user_id INTEGER, date TEXT, user_choose TEXT, bot_choose TEXT, result TEXT)")
        cursor.execute("INSERT INTO rock_paper_scissors_classical_history (user_id, date) VALUES (?, ?)", (user_id, date))
    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "classical_RPC",
               "id": f"{date}",
               "choose": "r"}
    callback = payload_to_callback(payload)
    rock_button = InlineKeyboardButton(text="Камень", callback_data=callback)

    payload = {"type": "action",
               "command": "classical_RPC",
               "id": f"{date}",
               "choose": "p"}
    callback = payload_to_callback(payload)
    paper_button = InlineKeyboardButton(text="Бумага", callback_data=callback)

    payload = {"type": "action",
               "command": "classical_RPC",
               "id": f"{date}",
               "choose": "s"}
    callback = payload_to_callback(payload)
    scissors_button = InlineKeyboardButton(text="Ножницы", callback_data=callback)

    payload = {"type": "action",
               "command": "classical_RPC",
               "id": f"{date}",
               "choose": "c"}
    callback = payload_to_callback(payload)
    cancel_button = InlineKeyboardButton(text="Остановить игру (назад)", callback_data=callback)

    markup.row(rock_button, scissors_button, paper_button)
    markup.row(cancel_button)

    return markup


def stop_classical_rock_paper_scissors(user_id, date):
    """
    Функция для остановки игры
    :param user_id: id пользователя
    :param date: время старта
    :return: str answer
    """
    with sqlite3.connect(f'{path}admindb/databases/minigames.db') as con:
        cursor = con.cursor()
        cursor.execute("SELECT * FROM rock_paper_scissors_classical_history WHERE user_id = ? AND date = ?", (user_id, date))
        data = cursor.fetchone()
        if data is None:
            return "Игра не найдена, возможно уже остановлена. Можешь начать новую"
        else:
            cursor.execute("DELETE FROM rock_paper_scissors_classical_history WHERE user_id = ? AND date = ?", (user_id, date))
            con.commit()
            return "Игра остановлена"


def classical_rock_paper_scissors(user_id, date, user_choose):
    """
    Функция для игры в обычный камень-ножницы-бумага с ботом
    :param user_id: id пользователя
    :param date: время старта
    :param user_choose: выбор пользователя (r - камень, p - бумага, s - ножницы)
    :return: str answer
    """
    with sqlite3.connect(f'{path}admindb/databases/minigames.db') as con:
        cursor = con.cursor()
        cursor.execute("SELECT * FROM rock_paper_scissors_classical_history WHERE user_id = ? AND date = ?", (user_id, date))
        data = cursor.fetchone()
        if data is None:
            return "Игра не найдена, возможно уже остановлена. Начни заново"
        else:
            cursor.execute("UPDATE rock_paper_scissors_classical_history SET user_choose = ? WHERE user_id = ? AND "
                           "date = ?", (user_choose, user_id, date))
            bot_choose = random.choice(["r", "p", "s"])
            cursor.execute("UPDATE rock_paper_scissors_classical_history SET bot_choose = ? WHERE user_id = ? AND "
                           "date = ?", (bot_choose, user_id, date))
            if bot_choose == "r":
                if user_choose == "r":
                    result = "Ничья"
                elif user_choose == "p":
                    result = "Победа"
                elif user_choose == "s":
                    result = "Поражение"
            elif bot_choose == "p":
                if user_choose == "r":
                    result = "Поражение"
                elif user_choose == "p":
                    result = "Ничья"
                elif user_choose == "s":
                    result = "Победа"
            elif bot_choose == "s":
                if user_choose == "r":
                    result = "Победа"
                elif user_choose == "p":
                    result = "Поражение"
                elif user_choose == "s":
                    result = "Ничья"
            cursor.execute("UPDATE rock_paper_scissors_classical_history SET result = ? WHERE user_id = ? AND "
                            "date = ?", (result, user_id, date))
    if user_choose == "r":
        readable_user_choose = "камень"
    elif user_choose == "p":
        readable_user_choose = "бумагу"
    elif user_choose == "s":
        readable_user_choose = "ножницы"

    if bot_choose == "r":
        readable_bot_choose = "камень"
    elif bot_choose == "p":
        readable_bot_choose = "бумагу"
    elif bot_choose == "s":
        readable_bot_choose = "ножницы"

    answer = f"{result}!\n\nТы выбрал {readable_user_choose}\nЯ выбрал {readable_bot_choose}"
    return answer



