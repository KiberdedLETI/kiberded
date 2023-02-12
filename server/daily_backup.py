# dependencies: []
"""
Бот, при запуске отправляет ежедневные бэкапы в специальную беседу в телеграме.
Также можно просто send_file(file_path, name), она отправляет файл в эту же беседу.
"""


import telebot
import toml
import logging
import sys
import os
from datetime import datetime
import sqlite3

logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)

try:
    config = toml.load('./configuration.toml')  # если импортируется из корня
except FileNotFoundError:
    try:
        config = toml.load('../configuration.toml')  # если импортируется из папки server
    except FileNotFoundError:
        logger.critical('configuration.toml не найден!')
        sys.exit()

token = config.get('Kiberded').get('token_telegram_backup')
path = config.get('Kiberded').get('path')

bot = telebot.TeleBot(token)


def send_file(file_path, name):
    if os.path.isfile(file_path):
        doc = open(file_path, 'rb')
        mes = bot.send_document(-640134320, doc, visible_file_name=name)
        return mes.document.file_id
    else:
        mes = bot.send_message(-640134320, "Файл не существует")
        logger.error('Файл не существует')
        return 0


def write_file_id_to_db(date, type, file_id):
    with sqlite3.connect(f'{path}admindb/backups.db') as con:
        con.execute("""INSERT INTO backups (date, type, file_id) VALUES (?, ?, ?) """, [date, type, file_id])
        con.commit()


if __name__ == '__main__':
    now = datetime.now()
    file = now.strftime('%Y-%m-%d_00-01')
    mes1 = send_file(f'../../backups/databases/{file}.tar.gz', f'Databases_{file[:-6]}.tar.gz')
    mes2 = send_file(f'../../backups/keyboards/{file}.tar.gz', f'Keyboards_{file[:-6]}.tar.gz')
    mes3 = send_file(f'../../backups/keyboards_telegram/{file}.tar.gz', f'keyboards_telegram_{file[:-6]}.tar.gz')
    mes4 = send_file(f'../../backups/messages_backup/{file}.tar.gz', f'messages_backup_{file[:-6]}.tar.gz')

    if mes1:
        write_file_id_to_db(file[:-6], 'Databases', mes1)
    if mes2:
        write_file_id_to_db(file[:-6], 'Keyboards', mes2)
    if mes3:
        write_file_id_to_db(file[:-6], 'keyboards_telegram', mes3)
    if mes4:
        write_file_id_to_db(file[:-6], 'messages_backup', mes4)
