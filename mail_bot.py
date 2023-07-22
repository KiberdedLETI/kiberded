#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# dependencies: [mail_bot]

"""
Почтовый скрипт бота - проверка почтовых ящиков и отправка сообщения о новом письме
"""

import imaplib
import email
import base64
import math
import os
import quopri
import sqlite3
import sys
import time
import toml
import vk_api
from vk_api.utils import get_random_id
import telebot
from telebot import custom_filters
import traceback
import logging

logger = logging.getLogger('mail_bot')
console_handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)

notified_groups = []  # массив для групп (модераторов), которым отправилось сообщение об ошибке

try:
    config = toml.load('configuration.toml')
except FileNotFoundError:
    logger.critical('configuration.toml не найден!')
    sys.exit()

token = config.get('Kiberded').get('token')
tg_token = config.get('Kiberded').get('token_telegram')
tg_admin_chat = config.get('Kiberded').get('telegram_admin_chat')

path = config.get('Kiberded').get('path')

bot = telebot.TeleBot(tg_token)

global vk


def send_message(message, chat_id):
    """
    Отправка сообщения с обработкой Flood-control

    :param int chat_id: id беседы для отправки сообщения.
    :param str message: сообщение, обязательный аргумент
    """

    try:
        vk.messages.send(
            chat_id=chat_id,
            random_id=get_random_id(),
            message=message)
    except vk_api.exceptions.ApiError as vk_error:
        if '[9]' in vk_error:  # ошибка flood-control: если флудим, то ждем секунду ответа
            time.sleep(1)
            send_message(message, chat_id)
            logger.warning('Flood-control, спим секунду')
        elif '[914]' in str(vk_error):  # message is too long
            print(f'Сообщение слишком длинное, разбиваем на части')
            for i in range(math.floor(len(message)/4096)):  # разбиение сообщение на части по 4кб
                send_message(message[i*4096:i*4096+4096], chat_id)
            if len(message)%4096 != 0:  # последний кусок сообщения
                send_message(message[-(len(message)%4096):], chat_id)


def send_tg_message(chat_id, text, **kwargs) -> telebot.types.Message:
    """
    Функция отправки сообщений. Создана одновременно и для обхода ограничения на максимальную длину текста, и для
    автодампа сообщения. Возвращается API-reply отправленного сообщения; если текст больше 4096 символов - то оно
    делится и возвращается api-peply последнего отправленного сообщения

    !!! Здесь без дампа сообщения, privacy так сказатьб

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


def decodestr(string, type_str):
    if string.find('?') != -1:
        new_string = string[0:string.find('?')]
        string = new_string
    if type_str == 'b' or type_str == 'B':
        result = base64.b64decode(string)
    elif type_str == 'q' or type_str == 'Q':
        result = quopri.decodestring(string)
    else:
        logger.error(f'Ошибка в преобразовании строки (функция decodestr): неизвестный тип кодирования, аргументы '
              f'string = {string}, type_str = {type_str}\n{traceback.format_exc()}')
        result = 'хз'
    return result


def str2readable(string):
    try:
        if string.find('=?') != -1:
            string = string[string.find('=?'):]
        if string[0:2] == '=?':
            second_ques = string.index('?', 2)
            code_str = string[2:second_ques]
            type_code = string[second_ques + 1]
            rightequal_index = string.rindex('=')
            work_str = string[second_ques + 3:rightequal_index - 1]
            decoded_str = decodestr(work_str, type_code)
            if code_str == 'utf-8' or code_str == 'UTF-8':
                resultstring = decoded_str.decode("utf-8") + string[rightequal_index + 1:]
            elif code_str == 'koi8-r' or code_str == 'KOI8-r' or code_str == 'KOI8-R':
                resultstring = decoded_str.decode("koi8-r") + string[rightequal_index + 1:]
            elif code_str == 'windows-1251' or code_str == 'WINDOWS-1251':
                resultstring = decoded_str.decode("windows-1251") + string[rightequal_index + 1:]
            else:
                try:
                    resultstring = decoded_str.decode("windows-1251") + string[rightequal_index + 1:]
                except:
                    logger.error(f"Ошибка в преобразовании строки: неизвестная кодировка\n{traceback.format_exc()}")
                    resultstring = 'хз'
            return resultstring
        else:
            return string
    except:
        logger.error(f'Ошибка в преобразовании строки\n{traceback.format_exc()}')
        return 'хз'


def get_message(num, imap_url, login, password, vk):  # получает последнее письмо
    try:
        mail = imaplib.IMAP4_SSL(imap_url)
        mail.login(login, password)
        mail.list()
        mail.select()
        result, data = mail.uid('fetch', num, '(RFC822)')
        message = email.message_from_bytes(data[0][1])
        message_from = str2readable(message['From'])
        message_subj = str2readable(message['Subject'])
        message_time = message['Date']
        return message_from, message_subj, message_time, message
    except Exception as e:
        logger.error(f'Произошла ошибка {login} (в функции get_message), пробуем еще раз через 20 секунд\n{traceback.format_exc()}')
        error_str = f'Произошла ошибка {login} в get_message: {str(e)}'
        send_message(error_str, 1)
        time.sleep(5)
        get_message(num, imap_url, login, password, vk)


def get_uid(imap_url, login, password, vk, group):
    try:
        mail = imaplib.IMAP4_SSL(imap_url)
        try:  # Отдельная обработка неудачного входа на почту
            mail.login(login, password)
        except imaplib.IMAP4.error as auth_error:
            logger.error(f"Ошибка аутентификации {group} {login} ({auth_error})")
            return None
        mail.list()
        mail.select()
        result, data_ids = mail.uid('search', None, "ALL")
        mail_ids = data_ids[0].split()
        if mail_ids:
            return mail_ids[-1]
        else:
            logger.error(f"{group} {login} Ошибка в получении uid; data_ids:{data_ids}")
        return None

    except ArithmeticError as e:  # обработка сранья
        if '[Errno 104]' in str(e) or 'command SEARCH' in str(e) or '[Errno -3]' in str(e) or '[Errno 101]' in str(e):  # todo что это за ошибки?
            pass
        else:
            logger.error(f'Произошла ошибка {login} (в функции get_uid), пробуем еще раз через 5 секунд\n{traceback.format_exc()}')
            # notify_moderator(f'На вашей почте {login} что-то сломалось: \n{e}', group=group)
            time.sleep(5)
            get_uid(imap_url, login, password, vk, group)


def chat_params():  # достает всю таблицу group_gcals в массив.
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        ans = []
        for row in cur.execute("SELECT mail FROM group_gcals").fetchall():
            if row[0]:  # не добавляем тех у кого нет почты
                ans.append(cur.execute('SELECT vk_chat_id, group_id, mail, mail_password, mail_imap, tg_chat_id '
                                       'FROM group_gcals WHERE mail=?', [row[0]]).fetchone())
    con.close()
    return ans


def notify_moderator(error_message, group):
    with sqlite3.connect(f'{path}admindb/databases/admins.db') as con:
        cur = con.cursor()
        moderator_id = cur.execute('SELECT id FROM users WHERE group_id=?', [group]).fetchone()
        if moderator_id:
            moderator_id = moderator_id[0]
            if moderator_id in notified_groups:
                logger.warning(f'Сообщение об ошибке уже отправлялось')
                return 0
        else:
            logger.warning(f'Сообщение об ошибке не удалось отправить - нет модератора {group}')
            return 0
    try:
        vk.messages.send(
            user_id=moderator_id,
            random_id=get_random_id(),
            message=error_message)
        notified_groups.append(moderator_id)  # добавляем в список тех, кому отправилось сообщение
        logger.warning(f'Сообщение об ошибке отправлено модератору {group} @id{moderator_id}')

    except Exception as e:
        logger.warning(f'Сообщение об ошибке не удалось отправить @id{moderator_id}\n{e}')
    return 0


def main_func():
    global vk
    all_chats = chat_params()  # вся инфа из group_ids.db
    logger.info(f'Полученные данные из group_ids.db: \n{all_chats}')
    login = 'login error'  # для логов
    group = '0000'
    imap_url = 'imap_url error'
    
    vk_session = vk_api.VkApi(token=token)
    vk = vk_session.get_api()
    start_id_int = [0] * len(all_chats)  # пустой массив для хранения последних uid
    send_message('Почтовый на связи', 1)
    send_tg_message(tg_admin_chat, 'Почтовый на связи')
    logger.warning('Бот успешно включен, сон 2 секунды.')
    time.sleep(2)
    while True:
        for i in range(len(all_chats)):
            try:
                chat_id = str(int(all_chats[i][0][1:]))  # (peer_id -> chat_id)
                group = all_chats[i][1]
                login = all_chats[i][2]
                password = all_chats[i][3]
                imap_url = all_chats[i][4]
                tg_chat_id = all_chats[i][5]

                now_uid = get_uid(imap_url, login, password, vk, group)
                if now_uid is None:
                    continue

                now_id_int = int(str(now_uid)[2:-1])
                logger.info(f'{group} {login} - {now_id_int}')
                if start_id_int[i] != now_id_int and start_id_int[i] != 0:
                    start_id_int[i] = now_id_int
                    now_uid = str.encode(str(now_id_int))
                    fromstr, subjstr, timestr, messtr = get_message(now_uid, imap_url, login, password, vk)
                    stringtovk = f' пришло новое письмо от: {fromstr}, тема: {subjstr}...'

                    send_message(stringtovk, chat_id)
                    if tg_chat_id:
                        send_tg_message(tg_chat_id, stringtovk)

                    logger.warning(
                        f'Получено новое письмо, сообщение отправлено группе {group}. Текущий uid: {str(now_id_int)}')
                start_id_int[i] = now_id_int
                time.sleep(8)

            except ConnectionResetError:
                logger.warning(f'{group} {login} {imap_url} - connection_error: {traceback.format_exc()}')

            except imaplib.IMAP4.error:
                logger.warning(f'{group} {login} {imap_url} - imap_error: {traceback.format_exc()}')
                # todo обработка гугловской ошибки Application-specific password required
                # notify_moderator(f'Ошибка подключения к почте {login}: \nОтключен IMAP или неверные данные для входа\n'
                #                  f'Сбрось почту в настройках бота или проверь настройки почтового ящика', group=group)

            except ValueError as value_error:
                if 'invalid literal for int() with base 10:' in str(value_error):
                    pass  # ошибка invalid literal for int() with base 10: 'n' или 'error'
                else:
                    raise ValueError(value_error)

            except OSError as os_error:
                if '[Errno 101]' in str(os_error):  # ошибка OSError: Network is unreachable
                    pass
                elif '[Errno -3]' in str(os_error): # Exception: [Errno -3] Temporary failure in name resolution
                    pass
                elif 'EOF occurred in violation of protocol'  in str(os_error):
                    pass
                else:
                    raise Exception(os_error)

            except vk_api.exceptions.ApiError as vk_error:
                logger.warning(f'{group} {login} {imap_url} - vk_error: {traceback.format_exc()}')
                if '[7]' in str(vk_error):  # ошибка [7] Permission denied: the user was kicked out of the conversation'
                    pass
                else:
                    raise Exception(vk_error)

            except Exception as e:
                try:
                    logger.critical(f'Произошла глобальная ошибка почтового: {group} - {login}{imap_url}\n{traceback.format_exc()}')
                    error_str = f'Произошла глобальная ошибка почтового: {group} - {login}{imap_url}\n {str(e)}\n{traceback.format_exc()}'
                    send_message(error_str, 1)
                except Exception as error_vk:
                    logger.critical(f'Не удалось отправить сообщение об ошибке в вк: {str(error_vk)}')

            continue
main_func()
