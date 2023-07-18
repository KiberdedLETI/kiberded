#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# dependencies: []

"""
Рассылка сообщений пользователям/в беседы (команда send_message)
"""

import math
import time
import traceback

import requests
import vk_api
from vk_api.utils import get_random_id
import sys
import sqlite3
import toml

import telebot

from datetime import datetime
import pickle


try:
    config = toml.load('./configuration.toml')  # если импортируется из корня
except FileNotFoundError:
    try:
        config = toml.load('../configuration.toml')  # если импортируется из папки server
    except FileNotFoundError:
        print('configuration.toml не найден!')
        sys.exit()

path = config.get('Kiberded').get('path')
token = config.get('Kiberded').get('token')
tg_token = config.get('Kiberded').get('token_telegram')
tg_admin_chat = config.get('Kiberded').get('telegram_admin_chat')

bot = telebot.TeleBot(tg_token)

global vk

now_date = datetime.now().strftime('%Y-%m-%d')  # необходимо для бэкапов сообщений


def send_message(message: str, peer_id, attachment=''):
    """
    Отправка сообщения с обработкой Flood-control

    :param str message: сообщение, обязательный аргумент
    :param int peer_id: id беседы или пользователя для отправки сообщения.
    :param attachment: вложение (опционально)
    """

    try:
        vk.messages.send(
            peer_id=peer_id,
            random_id=get_random_id(),
            message=message,
            attachment=attachment)
        print(f'Сообщение отправлено:'
              f'\npeer_id={peer_id}'
              f'\nmessage={message}'
              f'\nattachment={attachment if attachment else "None"}')

    except vk_api.exceptions.ApiError as vk_error:
        if '[9]' in str(vk_error):  # ошибка flood-control: если флудим, то ждем секунду ответа
            time.sleep(1)
            send_message(message, peer_id)
            print('Flood-control, спим секунду')
        elif ('[7]' or '[917]') in str(vk_error):  # Permission to perform this action is denied
            print(f'Сообщение не отправлено: message={message}, peer_id={peer_id},'
                  f' traceback:\n{traceback.format_exc()}')
        elif '[914]' in str(vk_error):  # message is too long
            print(f'Сообщение слишком длинное, разбиваем на части')
            for i in range(math.floor(len(message)/4096)):  # разбиение сообщение на части по 4кб
                send_message(message[i*4096:i*4096+4096], peer_id)
            if len(message)%4096 != 0:  # последний кусок сообщения
                send_message(message[-(len(message)%4096):], peer_id, attachment)
            elif attachment:  # если вдруг длина сообщения кратна 4кб и есть вложение - отправляем его без текста
                send_message(message='', peer_id=peer_id, attachment=attachment)
        else:
            raise Exception(vk_error)
    except requests.exceptions.ConnectionError:
        time.sleep(1)
        send_message(message, peer_id, attachment)


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
            dump_message(msg)
    else:
        msg = bot.send_message(chat_id, text, **kwargs)
        dump_message(msg)
    return msg


def get_user(group):  # принимает номер группы и возвращает user_id, если есть
    with sqlite3.connect(f'{path}/admindb/databases/admins.db') as con:
        cur = con.cursor()
        users = cur.execute('SELECT id FROM users WHERE group_id=?', [group]).fetchall()
    return users


def get_chat(group):  # принимает номер группы и возвращает peer_id, если есть
    with sqlite3.connect(f'{path}/admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        chats = cur.execute('SELECT chat_id FROM group_gcals WHERE group_id=?', [group]).fetchall()
    return chats


def get_users():  # возвращает user_id всех пользователей
    with sqlite3.connect(f'{path}/admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        users = cur.execute('SELECT user_id FROM user_ids').fetchall()
    return users


def get_chats():  # возвращает все peer_id
    with sqlite3.connect(f'{path}/admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        chats = cur.execute('SELECT chat_id FROM group_gcals').fetchall()
    return chats


def get_content(counter=3):  # возвращает текст для отправки и вложение, если есть
    try:
        message = ''
        attachment = ''
        is_attachment = False
        if sys.argv[1][:11] == 'attachment=':
            is_attachment = True
            attachment = sys.argv[1][11:]
            counter += 1
        message_list = sys.argv[counter:]
        for argument in message_list:
            message += f'{argument} '
        return message, is_attachment, attachment
    except IndexError:
        print('Неверные аргументы, см. ded send_message help')
        sys.exit()


vk_session = vk_api.VkApi(token=token)
vk = vk_session.get_api()

message, is_attachment, attachment = get_content()

index_counter = 2 if is_attachment else 1

try:
    if sys.argv[index_counter] in ['-c', '--chat', 'чат']:  # отправка в беседу через peer_id
        chat_id = sys.argv[index_counter+1]
        try:
            peer_id = int(chat_id) + 2000000000
            send_message(message, peer_id, attachment)
        except ValueError:
            print(f'Некорректный chat_id: {chat_id}. Сообщение не отправлено')

    elif sys.argv[index_counter] in ['-u', '--user', 'юзер']:  # отправка юзеру через user_id
        peer_id = sys.argv[index_counter+1]
        send_message(message, peer_id, attachment)

    elif sys.argv[index_counter] in ['-m', '--moderator', 'модератор']:  # отправка модератору группы (из admins.db)
        users = get_user(sys.argv[index_counter+1])
        if len(users):
            for user in users:
                peer_id = user[0]
                send_message(message, peer_id, attachment)
        else:
            print(f'Нет модераторов в группе {sys.argv[index_counter+1]}')

    elif sys.argv[index_counter] in ['-g', '--group', 'группа']:  # отправка в конфу группы (из group_ids.db)
        chats = get_chat(sys.argv[index_counter+1])
        if len(chats):
            for chat in chats:
                peer_id = chat[0]
                send_message(message, peer_id, attachment)
        else:
            print(f'Нет группы {sys.argv[index_counter+1]}')

    elif sys.argv[index_counter] in ['-a-G', '--all-groups', 'всем-группам']:  # отправка всем группам в конфу
        message, is_attachment, attachment = get_content(2)
        chats = get_chats()
        if len(chats):
            for chat in chats:
                peer_id = chat[0]
                send_message(message, peer_id, attachment)
        else:
            print(f'Нет групп')

    elif sys.argv[index_counter] in ['-a-U', '--all-users', 'всем-юзерам']:  # отправка всем юзерам
        message, is_attachment, attachment = get_content(2)
        users = get_users()
        if len(users):
            for user in users:
                peer_id = user[0]
                send_message(message, peer_id, attachment)
        else:
            print(f'Нет юзеров, мб слетела база')

    elif sys.argv[index_counter] in ['-h', '--help', 'справка']:  # вызов справки
        print('Без аргументов - отправка сообщения в отладочную конфу + в ТГ\n'
              '\t-c | чат PARAM - отправка сообщения в конфу с произвольным chat_id (осторожно!!!)\n'
              '\t-u | юзер PARAM- отправка сообщения юзеру (или конфу через peer_id) с произвольным user_id\n'
              '\t-m | модератор PARAM- отправка сообщения модераторам определенной группы\n'
              '\t-g | группа PARAM - отправка сообщения в беседы определенной группы\n'
              '\t-a-U | всем-юзерам PARAM - отправка сообщения всем юзерам\n'
              '\t-a-G | всем-группам PARAM - отправка сообщения во все беседы')

    else:  # отправка в отладочную
        message, is_attachment, attachment = get_content(1)
        send_message(message, 2000000001, attachment)
        send_tg_message(tg_admin_chat, message)

except IndexError:
    print('Недостаточно аргументов, см. ded help')
