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

bot = telebot.TeleBot(token)


def send_file(file_path, name):
    if os.path.isfile(file_path):
        doc = open(file_path, 'rb')
        bot.send_document(-640134320, doc, visible_file_name=name)
    else:
        bot.send_message(-640134320, "Файл не существует")
        logger.error('Файл не существует')


if __name__ == '__main__':
    now = datetime.now()
    file = now.strftime('%Y-%m-%d_00-01')
    send_file(f'../../backups/databases/{file}.tar.gz', f'Databases_{file[:-6]}.tar.gz')
    send_file(f'../../backups/keyboards/{file}.tar.gz', f'Keyboards_{file[:-6]}.tar.gz')
    send_file(f'../../backups/keyboards_telegram/{file}.tar.gz', f'keyboards_telegram_{file[:-6]}.tar.gz')
    send_file(f'../../backups/messages_backup/{file}.tar.gz', f'messages_backup_{file[:-6]}.tar.gz')
