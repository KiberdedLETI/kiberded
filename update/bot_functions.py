"""
Скрипт для простого импорта и отправки сообщений юзерам и в админскую беседу
"""
import toml
import logging
import sys
from telebot import telebot

import vk_api
from vk_api.utils import get_random_id

logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)


try:
    config = toml.load('./configuration.toml')  # если импортируется из корня
except FileNotFoundError:
    try:
        config = toml.load('../configuration.toml')  # если импортируется из папки update (скорее всего так и есть)
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


def send_telegram_message(message, chat_id=telegram_admin_chat):
    bot.send_message(chat_id, message)


def send_vk_message(message, peer_id=2000000001):
    vk.messages.send(
        peer_id=peer_id,
        random_id=get_random_id(),
        message=message)


def get_web_secret():
    return web_secret
