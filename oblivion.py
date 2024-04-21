#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# dependencies: []

"""
Финальное задание деда по рассылке прощальной речи. 
Эдакий апофеоз с небольшой надеждой на будущую реинкарнацию и второе пришествие. Но уже, вероятно, от других Создателей.
"""

import vk_api
from vk_api.utils import get_random_id
import telebot
import toml
import sys
import logging
import time
import traceback
from datetime import datetime, date, timedelta
import math
import sqlite3
import pickle


global config
global vk_session
global vk
global num_of_base

# common init
logger = logging.getLogger('oblivion')
console_handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)

try:
    config = toml.load('configuration.toml')
except FileNotFoundError:
    logger.critical('configuration.toml не найден!')
    sys.exit()

token = config.get('Kiberded').get('token')
tg_token = config.get('Kiberded').get('token_telegram')
path = config.get('Kiberded').get('path')
tg_admin_chat = config.get('Kiberded').get('telegram_admin_chat')
# /common init

bot = telebot.TeleBot(tg_token)
now_date = datetime.now().strftime('%Y-%m-%d') 


def send_message(message, peer_id, attachment=''):
    """
    Отправка сообщения с обработкой Flood-control

    :param int peer_id: id беседы или пользователя для отправки сообщения.
    :param str message: сообщение, обязательный аргумент
    :param attachment: вложение (опционально)
    """

    try:
        return vk_session.method("messages.send", {'v': 5.131,
                                                   'random_id': get_random_id(),
                                                   'message': message,
                                                   'attachment': attachment,
                                                   'peer_ids': peer_id})
    except vk_api.exceptions.ApiError as vk_error:
        if '[9]' in str(vk_error):  # ошибка flood-control: если флудим, то ждем секунду ответа
            time.sleep(1)
            send_message(message, peer_id)
            logger.warning('Flood-control, спим секунду')
        elif '[10]' in str(vk_error):  # Internal server error (чиво?)
            logger.warning(f'Сообщение не отправлено: {vk_error}, message={message}, peer_id={peer_id}')
        elif '[7]' in str(vk_error):  # Permission to perform this action is denied
            logger.warning(f'Сообщение не отправлено: {vk_error}, message={message}, peer_id={peer_id}')
        elif '[901]' in str(vk_error):  # Can't send messages for users without permission
            logger.warning(f'Сообщение не отправлено: {vk_error}, message={message}, peer_id={peer_id}')
        elif '[914]' in str(vk_error):  # message is too long
            print(f'Сообщение слишком длинное, разбиваем на части')
            for i in range(math.floor(len(message)/4096)):  # разбиение сообщение на части по 4кб
                send_message(message[i*4096:i*4096+4096], peer_id)
            if len(message) % 4096 != 0:  # последний кусок сообщения
                send_message(message[-(len(message) % 4096):], peer_id, attachment)
            elif attachment:  # если вдруг длина сообщения кратна 4кб и есть вложение - отправляем его без текста
                send_message(message='', peer_id=peer_id, attachment=attachment)
        elif '[925]' in str(vk_error):
            pass
        else:
            logger.error(f'Сообщение не отправлено: measage={message}, peer_id={peer_id}')
            raise Exception(vk_error)



def send_tg_message(chat_id, text, **kwargs) -> telebot.types.Message:
    """
    Функция отправки сообщений. Создана одновременно и для обхода ограничения на максимальную длину текста, и для
    автодампа сообщения. Возвращается API-reply отправленного сообщения; если текст больше 4096 символов - то оно
    делится и возвращается api-peply последнего отправленного сообщения
    Telegram documentation: https://core.telegram.org/bots/api#sendmessage

    :param chat_id: Unique identifier for the target chat or username of the target channel (in the format
    @channelusername)
    :param text: Text of the message to be sent
    :param parse_mode: Send Markdown or HTML, if you want Telegram apps to show bold, italic, fixed-width text or inline
     URLs in your bot's message.
    :param entities: List of special entities that appear in message text, which can be specified instead of parse_mode
    :param disable_web_page_preview: Disables link previews for links in this message
    :param disable_notification: Sends the message silently. Users will receive a notification with no sound.
    :param protect_content: If True, the message content will be hidden for all users except for the target user
    :param reply_to_message_id: If the message is a reply, ID of the original message
    :param allow_sending_without_reply: Pass True, if the message should be sent even if the specified replied-to
    message is not found
    :param reply_markup: Additional interface options. A JSON-serialized object for an inline keyboard, custom reply
    keyboard, instructions to remove reply keyboard or to force a reply from the user.
    :param timeout:
    :return: API reply (JSON-serialized message object)
    """

    msg = 0  # дабы IDE не ругалась, далее эта переменная так и так перезапишется
    if len(text) > 4096:  # обход ограничения
        splitted_text = telebot.util.smart_split(text, chars_per_string=3000)
        for text in splitted_text:
            msg = bot.send_message(chat_id, text, **kwargs)
    else:
        msg = bot.send_message(chat_id, text, **kwargs)
    return msg


def get_users(source='vk') -> list:  # список юзеров
    """
    Получение списка всех пользователей

    :param str source: 'vk' / 'tg' - источник сообщения
    :return: список [(user_id, count), ...]
    """
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cursor = con.cursor()
        data = []

        for row in cursor.execute(f'SELECT * FROM user_ids WHERE {source}_id'):
            data.append((int(row[0]))) if source == 'vk' else data.append((int(row[4])))
    con.close()
    return data


def get_groups(source='vk') -> list:  # список бесед
    """
    Получение списка всех бесед

    :param str source: 'vk' / 'tg' - источник сообщения
    :return: список [(user_id, count), ...]
    """
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cursor = con.cursor()
        data = []

        for row in cursor.execute(f'SELECT * FROM group_gcals WHERE {source}_chat_id'):
            data.append((int(row[6]))) if source == 'vk' else data.append((int(row[7])))
    con.close()
    return data

def initialization():
    global vk_session
    global vk

    vk_session = vk_api.VkApi(token=token)
    vk = vk_session.get_api()

    send_message('Запуск "Обливиона"', 2000000001)
    send_tg_message(-1001668185586, 'Запуск "Обливиона"')
    logger.warning('Запуск "Обливиона"')
    return 0


if initialization():
    logger.critical('Инициализация пошла по одному месту.')
    sys.exit()

# all_vk_users = get_users('vk')
all_vk_users = []
all_tg_users = get_users('tg')

all_vk_groups = get_groups('vk')
all_tg_groups = get_groups('tg')

with open(f'{path}last_message.txt', 'r', encoding='utf-8') as file:
    message = file.read()

error_counts = 0
global_error = ''

for vk_user in all_vk_users:
    try:
        send_message(message, vk_user)
    except Exception as e:
        error_counts += 1
        global_error += f'vk_user {vk_user}\n'
        logger.warning(f'Произошла ошибка при выполнении Oblivion (vk_user {vk_user}): {str(e)}\n{traceback.format_exc()}')
        
for tg_user in all_tg_users:
    try:
        send_tg_message(tg_user, message, disable_web_page_preview=True)
    except Exception as e:
        error_counts += 1
        global_error += f'tg_user {tg_user}\n'
        logger.warning(f'Произошла ошибка при выполнении Oblivion (tg_user {tg_user}): {str(e)}\n{traceback.format_exc()}')
        
for vk_group in all_vk_groups:
    try:
        send_message(message, vk_group)
    except Exception as e:
        error_counts += 1
        global_error += f'vk_group {vk_group}\n'
        logger.warning(f'Произошла ошибка при выполнении Oblivion (vk_group {vk_group}): {str(e)}\n{traceback.format_exc()}')
        
for tg_group in all_tg_groups:
    try:
        send_tg_message(tg_group, message, disable_web_page_preview=True)
    except Exception as e:
        error_counts += 1
        global_error += f'tg_group {tg_group}\n'
        logger.warning(f'Произошла ошибка при выполнении Oblivion (tg_group {tg_group}): {str(e)}\n{traceback.format_exc()}')
        
send_tg_message(tg_admin_chat, f'Код Обливиона выполнен.\n\nПользователей ВК: {len(all_vk_users)}\nГрупп ВК: {len(all_vk_groups)}\nПользователей ТГ: {len(all_tg_users)}\nГрупп ТГ: {len(all_tg_groups)}\n\nВсего ошибок при отправке: {error_counts}\n\nСообщения не доставлены следующим адресатам:{global_error}')