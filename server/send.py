#! /usr/bin/env python3
# -*- coding: utf-8 -*-

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

global vk


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
        print('Без аргументов - отправка сообщения в отладочную конфу\n'
              '\t-c | чат PARAM - отправка сообщения в конфу с произвольным chat_id (осторожно!!!)\n'
              '\t-u | юзер PARAM- отправка сообщения юзеру (или конфу через peer_id) с произвольным user_id\n'
              '\t-m | модератор PARAM- отправка сообщения модераторам определенной группы\n'
              '\t-g | группа PARAM - отправка сообщения в беседы определенной группы\n'
              '\t-a-U | всем-юзерам PARAM - отправка сообщения всем юзерам\n'
              '\t-a-G | всем-группам PARAM - отправка сообщения во все беседы')

    else:  # отправка в отладочную
        message, is_attachment, attachment = get_content(1)
        send_message(message, 2000000001, attachment)

except IndexError:
    print('Недостаточно аргументов, см. ded help')
