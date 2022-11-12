#! /usr/bin/env python
# -*- coding: utf-8 -*-
# dependencies: []

"""
Парсер цитат из паблика "Цитатник СПбГЭТУ"
"""

import logging
import re
import time
import requests
import vk_api
from vk_api.utils import get_random_id
import sqlite3
import toml
import os
import sys

# init
logger = logging.getLogger('quotes_parser')
console_handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)

try:
    config = toml.load('configuration.toml')
except FileNotFoundError:
    logger.critical('configuration.toml не найден!')
    sys.exit()

path = config.get('Kiberded').get('path')
group_token = config.get('Kiberded').get('group_token')
group_id = 0
token = config.get('Kiberded').get('token')
vk_login = config.get('Kiberded').get('vk_ded_page_login')
vk_password = config.get('Kiberded').get('vk_ded_page_password')
# /init


def get_vk_wall_content(group_id="126643733") -> list:
    """
    Парсер содержимого стены сообщества.

    :param group_id: id сообщества (без "-")
    :return: список с содержимым стены
    """

    # Вход в Длюдеду
    vk_session = vk_api.VkApi(vk_login, vk_password)
    vk_session.auth()

    full_items = []

    # Получение данных
    items = vk_session.method('wall.get', {'owner_id': f"-{group_id}", 'count': 100, 'filter': 'owner'})
    total = items['count']
    print(f"Всего записей: {total}")

    full_items.extend([el['text'] for el in items['items']])

    # Если записей больше 100, то получаем остальные
    if total > 100:
        for i in range(1, total // 100 + 1):
            items = vk_session.method('wall.get', {'owner_id': f"-{group_id}", 'count': 100, 'filter': 'owner', 'offset': i * 100})
            full_items.extend([el['text'] for el in items['items']])
            print(f"Записей получено: {len(full_items)}")

    # На всякий можно еще и записывать в файл
    # with open('quotes.txt', 'w', encoding='utf-8') as f:
    #     f.write('||'.join(full_items))  # || - разделитель цитат

    return full_items


def get_quotes_from_vk_wall_content(content: list):
    """
    Обработка полученного списка содержимого стены сообщества - получаем цитаты и автора из каждого элемента
    и заносим в БД admindb/prepods_quotes.db (таблица quotes (surname, quote)).

    :param content: список с содержимым стены
    :return: 0
    """

    with sqlite3.connect(f'{path}admindb/databases/prepods.db') as con:
        con.row_factory = lambda cursor, row: row[0]  # чтобы возвращать list, а не list of tuples
        cur = con.cursor()
        query = 'SELECT surname FROM prepods'
        list_prepods_surnames = list(set(cur.execute(query).fetchall()))  # сразу без дубликатов
        # query = 'SELECT initials FROM prepods'
        # list_prepods_initials = cur.execute(query).fetchall()
    con.close()

    # Парсим цитаты
    quotes = {i: [] for i in list_prepods_surnames}

    for item in content:
        if '#' not in item:  # если в записи нет хештега, то это не цитата, пропускаем
            continue

        # Подпись имеет формат "#Абросимов_СПбГЭТУ" или "#Абросимов #СПбГЭТУ", отсюда достаем фамилию
        surname = re.search(r'#\w+', item).group()[1:].split('_')[0]

        if surname in list_prepods_surnames:
            # Если фамилия есть в БД, то парсим цитату - все содержимое до #
            quote = item.split('#')[0].strip()
            quotes[surname].append(quote)
            # print(f"Цитата автора {surname}: \n{quote}\n\n")
        else:
            print(f"Фамилия {surname} не найдена в БД. Пост: {item}")

    print(quotes)

    quotes = {k: v for k, v in quotes.items() if v}  # удаляем пустые списки

    # Заносим цитаты в БД
    with sqlite3.connect(f'{path}admindb/databases/prepods_quotes.db') as con:
        cur = con.cursor()
        for surname, quotes_list in quotes.items():
            for quote in quotes_list:
                query = f"INSERT INTO quotes (surname, quote) VALUES (?, ?)"
                cur.execute(query, (surname, str(quote)))
        con.commit()
    con.close()

    print('Цитаты занесены в БД, длина словаря:', len(quotes))
    return 0


if __name__ == '__main__':
    data = get_vk_wall_content()
    # with open('quotes.txt', 'r', encoding='utf-8') as f:
    #     data = f.read().split('||')
    get_quotes_from_vk_wall_content(data)