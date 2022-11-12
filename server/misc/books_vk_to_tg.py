# dependencies: [telegram_bot]
"""
Скрипт для автоматического переноса всех книг из вк (раздел "Файлы") в телеграм, и создания базы books_vk_tg.db
Собственно, при запуске загружается список всех документов из вк, и с определенным интервалом по одной книге
отправляется деду после команды /add_book. При запуске необходимо ввести телефон из вк и код подтверждения из смс.
Если книга уже существует в папке - то она будет пропущена, сравнение происходит по title.

Путь до бд и до книг лучше указывать полный, а не относительный, потому что иначе загрузка книг может поломаться
Необходимо выключить двухфакторную авторизацию как в тг, так и в вк.


Необходимо заполнить:

vk_login - логин или телефон вк
vk_password - пароль вк
vk_group_id - id группы вк (пользователь должен видеть все книги!)

tg_api_id - api id приложения в тг (через my.telegram.org, юзер должен быть хотя бы модератором для /add_book)
tg_api_hash - api hash приложения в тг
"""

import vk_api
from telethon import TelegramClient, sync
import sqlite3
import time
import os
import sys
import urllib.request

vk_login = ''
vk_password = ''
vk_group_id = '-201485931'

tg_api_id = ''
tg_api_hash = ''

path = ''  # путь для бд
path_books = ""  # ПОЛНЫЙ путь папки для книг

client = TelegramClient('session', tg_api_id, tg_api_hash)
client.start()


vk_session = vk_api.VkApi(vk_login, vk_password)

try:
    vk_session.auth(token_only=True)
except vk_api.AuthError as error_msg:
    print(error_msg)
    sys.exit(1)

tools = vk_api.VkTools(vk_session)
docs = tools.get_all('docs.get', 10000, {'owner_id': vk_group_id})
print(f'Получены книги: {docs}')

with sqlite3.connect(path) as con:
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS books_vk_tg (id INTEGER PRIMARY KEY, doc_link TEXT, file_link_tg TEXT)")
    con.commit()

    for doc in docs['items']:
        if f'{doc["title"]}.{doc["ext"]}' in os.listdir(path_books):
            print(f'Книга {doc["title"]}.{doc["ext"]} уже есть в базе')
            continue
        print(f'Загрузка книги: {doc["title"]}')
        filepath, _ = urllib.request.urlretrieve(doc["url"], f'{path_books}/{doc["title"]}.{doc["ext"]}')
        print(f'Добавляем книгу: {doc["title"]}')
        client.send_message('kiberded_leti_bot', '/add_book')
        client.send_file('kiberded_leti_bot', f'{path_books}/{doc["title"]}.{doc["ext"]}')
        time.sleep(2)
        messages = client.get_messages('kiberded_leti_bot', limit=2)
        text = messages[1].message
        file_id = text[29:text.rfind('\n\nИспользуй')]
        cur.execute("INSERT INTO books_vk_tg (doc_link, file_link_tg) VALUES (?, ?)", (f'doc{doc["owner_id"]}_{doc["id"]}', file_id))
        con.commit()
        print(f'Книга добавлена: {doc["title"]}')
        time.sleep(3)
