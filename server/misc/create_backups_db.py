# dependencies: []
"""
Скрипт для создания БД backups.db для дэшборда. Пользователь должен быть в бэкапной конфе, указанной в конфиге.
Необходимо выключить ДФ авторизацию в телеге

Необходимо заполнить:

tg_api_id - api id приложения в тг (через my.telegram.org, юзер должен быть хотя бы модератором для /add_book)
tg_api_hash - api hash приложения в тг
backup_chat_id - chat_id чата с бэкапами
"""

from telethon import TelegramClient
import sqlite3
tg_api_id = 0  # int
tg_api_hash = ''

backup_chat_id = 0  # id чата с бэкапами, int!!

path = 'C://Users//evgen//Desktop//backups.db'  # путь для бд

client = TelegramClient('session', tg_api_id, tg_api_hash)
client.start()

chat = client.get_entity(backup_chat_id)
messages = client.get_messages(chat)
messages = client.get_messages(chat, messages.total)


with sqlite3.connect(path) as con:
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS backups (date TEXT, type TEXT, file_id TEXT)")
    con.commit()

    for message in messages:
        if message.file:
            name = message.file.name
            file_id = message.file.id

            name = name.split('_')
            if name[0] == 'messages':
                # явно это бэкап messages_backup
                type = 'messages_backup'
                date = name[2][:-7]  # отсекаем .tar.gz
                print(f'Файл {type}, дата {date}, file_id = {file_id}')
            elif name[0] == 'Databases':
                type = 'Databases'
                date = name[1][:-7]
                print(f'Файл {type}, дата {date}, file_id = {file_id}')
            elif name[0] == 'Keyboards':
                type = 'Keyboards'
                date = name[1][:-7]
                print(f'Файл {type}, дата {date}, file_id = {file_id}')
            elif name[0] == 'keyboards':
                # клавы телеги
                type = 'keyboards_telegram'
                date = name[2][:-7]  # отсекаем .tar.gz
                print(f'Файл {type}, дата {date}, file_id = {file_id}')
            else:
                print(f'\nНеопознанный файл!!! name = {message.file.name}, пропускаем\n')
                continue
        else:
            print(f'\nСообщение - не файл! Текст сообщения: {message.text}, пропускаем... \n')
            continue

        cur.execute("""INSERT INTO backups (date, type, file_id) VALUES (?, ?, ?) """, [date, type, file_id])

