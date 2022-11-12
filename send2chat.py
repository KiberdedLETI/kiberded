#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# dependencies: []

import time
import traceback

import requests
import vk_api
from vk_api.utils import get_random_id
import sys
import os
import toml

path = f'{os.path.abspath(os.curdir)}/'

try:
    config = toml.load('./configuration.toml')  # если импортируется из корня
except FileNotFoundError:
    try:  # на случай, если вызывается из каки-то подпапок типа ./server или ./update ... может сломаться...
        config = toml.load('../configuration.toml')  # если импортируется из папки server
    except FileNotFoundError:
        sys.exit()


def send_message(message, vk, chat_id):
    try:
        vk.messages.send(
            chat_id=chat_id,
            random_id=get_random_id(),
            message=message)
    except vk_api.exceptions.ApiError as vk_error:
        if "[917]" in str(vk_error):
            print("Деда нет в данной конфе")
        else:
            raise Exception(vk_error)
    except requests.exceptions.ConnectionError:
        time.sleep(5)
        send_message(message, vk, chat_id)
    except Exception as e:
        send_message(f'Кто-то пытался пырнуть деда, но произошла ошибка. Сообщение: {message}, chat_id={chat_id}.\n'
                     f'Ошибка: {traceback.format_exc()}', vk, chat_id)


token = config.get('Kiberded').get('token')

vk_session = vk_api.VkApi(token=token)
vk = vk_session.get_api()
message = ''
k = 0
chat_id = 1
for param in sys.argv:
    if k == 0:
        k += 1
    else:
        if k == 1 and "--chat_id=" in str(param):
            chat_id_str = str(param)[10:]
            try:
                chat_id = int(chat_id_str)
            except ValueError:
                chat_id = 1
        else:
            message += str(param) + ' '
send_message(message, vk, chat_id)

