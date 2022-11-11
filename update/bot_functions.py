"""
Скрипт для простого импорта и отправки сообщений юзерам и в админскую беседу
"""
import toml
import logging
import sys
from telebot import telebot

import vk_api
from vk_api.utils import get_random_id
import pickle
from datetime import datetime
import os

logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)


try:
    config = toml.load('./configuration.toml')  # если импортируется из корня
    path = './'
except FileNotFoundError:
    try:
        config = toml.load('../configuration.toml')  # если импортируется из папки update (скорее всего так и есть)
        path = '../'
    except FileNotFoundError:
        logger.critical('configuration.toml не найден!')
        sys.exit()

token_telegram = config.get('Kiberded').get('token_telegram')
token_vk = config.get('Kiberded').get('token')
telegram_admin_chat = config.get('Kiberded').get('telegram_admin_chat')
web_secret = config.get('Kiberded').get('web_secret')  # не хочется засорять users.py огромным куском кода ради этого

bot = telebot.TeleBot(token_telegram)

vk_session = vk_api.VkApi(token=token_vk)
vk = vk_session.get_api()

now_date = datetime.now().strftime('%Y-%m-%d')  # необходимо для бэкапов сообщений


def create_backup_dir() -> int:  # написана с учетом ежедневной перезагрузки в 00:00
    """
    Создает папку path/messages_backups/date
    :return: 0 если все ок
    """

    folder = f'{path}messages_backup/{now_date}'
    if not os.path.isdir(f'{folder}'):
        os.mkdir(f'{folder}')
    return 0


def dump_message(message, callback=False) -> int:  # BIG Brother Is Watching You.
    """
    Функция для записи всех сообщений в pickle-файлы, дабы они потом собирались в одну гигантскую БД и хранились
    где-нибудь у админов. Не очень гуманно, но лучше так, чем никак.
    :param message: непосредственно сообщение, которое записывается в pickle
    :param callback: if True, то это callback_query, и формат файла будет call_.....
    :return: 0 если все ок
    """
    date = now_date
    date_mes = message.date
    chat_id = message.chat.id
    message_id = message.message_id  # чтобы точно задампились все сообщения, потому что могут быть удаленные и
    # отправленные несколько раз в секунду
    callback_str = 'call_output_' if callback else ''
    with open(f'{path}messages_backup/{date}/{callback_str}{date_mes}_{chat_id}_{message_id}.pickle', 'wb') as f:
        pickle.dump(message, f)

    return 0


def send_telegram_message(message, chat_id=telegram_admin_chat):
    msg = 0  # дабы IDE не ругалась, далее эта переменная так и так перезапишется
    if len(message) > 4096:  # обход ограничения
        splitted_text = telebot.util.smart_split(message, chars_per_string=3000)
        for message in splitted_text:
            msg = bot.send_message(chat_id, message)
            dump_message(msg)
    else:
        msg = bot.send_message(chat_id, message)
        dump_message(msg)
    return msg


def send_vk_message(message, peer_id=2000000001):
    vk.messages.send(
        peer_id=peer_id,
        random_id=get_random_id(),
        message=message)


def get_web_secret():
    return web_secret

create_backup_dir()
