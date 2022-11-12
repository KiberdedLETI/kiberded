#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# dependencies: [scheduler]

"""
Функции, выполняемые по расписанию - ежедневно и т.д.
"""

import sqlite3
import random
from vk_api.utils import get_random_id
import schedule
import time
from datetime import datetime, date, timedelta
import toml
import math
import vk_api
import telebot
import logging
import traceback
from bot_functions.anekdot import get_random_toast
from bot_functions.bots_common_funcs import get_last_lesson, read_calendar, read_table, get_day
from shiza.etu_parsing import parse_etu_ids, load_calendar_cache, load_table_cache, \
    parse_prepods_schedule, load_prepods_table_cache
from shiza.daily_functions import daily_cron, donator_daily_cron, get_exam_notification, get_groups, \
    get_anekdot_user_ids, get_user_table_ids
from shiza.databases_shiza_helper import generate_prepods_keyboards, generate_departments_keyboards, \
    create_departments_db
import sys
import pickle

global config
global vk_session
global vk
global num_of_base

# common init
logger = logging.getLogger('scheduler')
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
num_of_base = config.get('Kiberded').get('num_of_base')  # количество анекдотов в базе
path = config.get('Kiberded').get('path')
cron_time = config.get('Kiberded').get('cron_time')
tables_time = config.get('Kiberded').get('tables_time')
is_sendCron = config.get('Kiberded').get('is_sendCron')
is_sendToast = config.get('Kiberded').get('is_sendToast')
tg_admin_chat = config.get('Kiberded').get('telegram_admin_chat')
# /common init

bot = telebot.TeleBot(tg_token)
now_date = datetime.now().strftime('%Y-%m-%d')  # необходимо для бэкапов сообщений


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


def dump_message(message) -> int:  # BIG Brother Is Watching You.
    """
    Функция для записи всех сообщений в pickle-файлы, дабы они потом собирались в одну гигантскую БД и хранились
    где-нибудь у админов. Не очень гуманно, но лучше так, чем никак.
    :param message: непосредственно сообщение, которое записывается в pickle
    :return: 0 если все ок
    """
    date = now_date
    date_mes = message.date
    chat_id = message.chat.id
    message_id = message.message_id  # чтобы точно задампились все сообщения, потому что могут быть удаленные и
    # отправленные несколько раз в секунду
    with open(f'{path}messages_backup/{date}/schedule_{date_mes}_{chat_id}_{message_id}.pickle', 'wb') as f:
        pickle.dump(message, f)

    return 0


def unpin_tg_message(chat_id, message_id) -> bool:
    """
    Открепление сообщения в Telegram, при наличии
    todo проверить "If (message_id) not specified, the most recent pinned message (by sending date) will be unpinned.
        последнее сообщение от бота или вообще???

    :param chat_id: id чата
    :param message_id: id сообщения, которое нужно открепить
    :return: True, если сообщение успешно откреплено, False если нет
    """

    try:  # Не знаю, нужно ли обрабатывать ошибки, но пока так
        pin_st = bot.unpin_chat_message(chat_id=chat_id, message_id=message_id)
        return pin_st
    except Exception as e:
        logger.error(f'Ошибка при откреплении сообщения в Telegram: {e}')
        return False


def pin_tg_message(message, chat_type='group') -> bool:
    """
    Закрепление сообщения в Telegram, без отправки уведомления (зачем оно?),
    с записью message_id закрепленного сообщения в базу (для открепления в следующий раз)

    :param message: непосредственно сообщение
    :param str chat_type: 'group' - закрепление в группе, 'private' - закрепление в ЛС
    :return: True, если сообщение успешно закреплено, False если нет
    """

    if chat_type == 'group':
        query = f'UPDATE group_gcals SET tg_last_msg={message.message_id} WHERE tg_chat_id={message.chat.id}'
    elif chat_type == 'private':
        query = f'UPDATE user_ids SET tg_last_msg={message.message_id} WHERE telegram_id={message.chat.id}'
    else:
        raise Exception('неверный аргумент type в pin_tg_message')

    try:  # Не знаю, нужно ли обрабатывать ошибки, но пока так
        pin_st = bot.pin_chat_message(chat_id=message.chat.id, message_id=message.message_id, disable_notification=True)

        if pin_st:  # Обновляем данные о закрепе
            with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
                cur = con.cursor()
                cur.execute(query)
                con.commit()
            con.close()
        return pin_st

    except Exception as e:
        logger.error(f'Ошибка при закреплении сообщения в Telegram: {e}')
        return False


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


def pin_message(response, peer_id):  # закрепление сообщения (если есть права администратора беседы)
    try:
        message_id = response[0].get('conversation_message_id')
        vk_session.method('messages.pin', {"peer_id": peer_id, "conversation_message_id": message_id, "v": 5.131})
    except vk_api.exceptions.ApiError as vk_error:
        if '[9]' in str(vk_error):  # ошибка flood-control: если флудим, то ждем секунду ответа
            time.sleep(1)
            pin_message(message_id, peer_id)
            logger.warning('Flood-control, спим секунду')
        elif '[925]' in str(vk_error):
            pass
        else:
            raise Exception(vk_error)
    except TypeError as type_error:
        logger.warning(f'Сообщение не закреплено: {type_error}, peer_id={peer_id}')


def get_anekdot(num) -> str:
    """
    Чтение анекдота из базы под заданным номером

    :param int num: номер анекдота (0 - num_of_base)
    :return: анекдот.
    """

    with sqlite3.connect(f'{path}anekdots.db') as db:
        cursor = db.cursor()
        cursor.execute('SELECT text FROM anekdots WHERE id=?', [num])
        data = cursor.fetchall()
        text = data[0][0]
    if text == 'ERROR':
        get_anekdot(random.randint(0, num_of_base))
    anekdot_str = text[3:-4]
    return anekdot_str


def send_anekdot(user_id, num, target='vk'):
    """
    Чтение и отправка анекдота (get_anekdot -> send_message) с обработкой ошибок

    :param int user_id: id для отправки
    :param int num: номер анекдота (0 - num_of_base)
    :param str target: название приложения для отправки ('vk' или 'tg')
    :return: 0
    """

    try:
        anekdot_str = get_anekdot(num)

        if target == 'vk':
            send_message(anekdot_str, user_id)
        elif target == 'tg':
            send_tg_message(user_id, anekdot_str)

    except Exception as e:
        logger.error(f'Произошла ошибка при отправке анекдота адресату @id{str(user_id)}: {str(e)}')
    return 0


def cron():
    """
    Большая функция, в которой отправляются расписания и прочие штуки по беседам групп,
    а также обновляются данные БД каждой группы.

    :return:
    """

    # В начале курса, а также в первых месяцах новых семестров обновляем etu_ids
    if date.today().strftime('%m-%d') == '09-01':
        try:
            send_message(f"Парсинг etu_id's. Проверь корректность данных!!!:\n", 2000000001)
            admin_message = parse_etu_ids()  # обновлять эти айди нужно перед обновлением всех БД и прочего
            send_message(admin_message, 2000000001)
            # send_tg_message(tg_admin_chat, admin_message)
        except KeyError as e:
            send_message(e, 2000000001)
            # send_tg_message(tg_admin_chat, e)
        except Exception as e:
            err_message = f'Ошибка парсинга etu_id: {e}\n{traceback.format_exc()}'
            send_message(err_message, 2000000001)
            # send_tg_message(tg_admin_chat, err_message)
            logger.critical(f"{err_message}")

    # Раз в месяц обовляем расписание преподавателей
    if date.today().day == 3:
        parse_prepods_schedule()
        load_prepods_table_cache()
        create_departments_db()
        generate_departments_keyboards()
        generate_prepods_keyboards()

    # структура сообщения: донатное (добавляется последним) + daily_cron() + расписание/календарь (все при наличии)

    load_calendar_cache()  # На всякий обновляем кэш календаря перед отправкой расписания
    load_table_cache()

    groups, gcal_lnks, chat_ids, tg_chat_ids, tg_last_messages = get_groups()
    schedule_counter = 0  # счетчик отправленных сообщений
    calendar_counter = 0  # счетчик отправленных календарей

    send_message('Ежедневный крон', 2000000001)
    send_tg_message(tg_admin_chat, 'Ежедневный крон')

    for k in range(len(groups)):
        group = groups[k]
        peer_id = chat_ids[k]  # str, только для сообщения об ошибке
        tg_chat = tg_chat_ids[k]  # int, для отправки в Telegram
        tg_last_message = tg_last_messages[k]  # int, для открепления в Telegram

        try:
            # Если нет беседы группы, то просто обновляем бд и пропускаем составление сообщения ей
            if not chat_ids[k] and not tg_chat_ids[k]:
                daily_cron(group)
                continue

            # иначе собираем данные для сообщений - изменения в параметрах группы
            if chat_ids[k]:
                peer_id = int(chat_ids[k])
            if tg_chat_ids[k]:
                tg_chat = int(tg_chat_ids[k])

            # обновление данных - изменения в учебном состоянии (семестр/сессия)
            is_exam, is_study, daily_str = daily_cron(group)

            # если и то и то =True -> есть расписание сессии, но семестр еще идет (заканчивается, скорее всего)
            if is_exam and is_study:
                is_exam = 0  # тогда оставляем пока обычное расписание

            please_donate, attachment = donator_daily_cron(group)  # ежедневная пикча и уведомление о ее отключении

            # сообщение отправляется либо с календарем, либо с расписоном. от этого две сборки сообщения
            if gcal_lnks[k]:  # если есть календарь
                calendar_message = read_calendar(group)
                if calendar_message.split()[-1] != 'Пусто':  # только дни когда что-то есть
                    # Отправка ВК
                    if peer_id:
                        response = send_message(message=please_donate + daily_str + calendar_message,
                                                peer_id=peer_id,
                                                attachment=attachment)
                        pin_message(response, peer_id)
                        logger.warning(f'Календарь отправлен группе {group}')

                    # Отправка ТГ
                    if tg_chat:
                        if tg_last_message:  # Открепляем предыдущее, если оно было todo check
                            unpin_tg_message(tg_chat, tg_last_message)
                        msg = send_tg_message(tg_chat, please_donate + daily_str + calendar_message)
                        pin_tg_message(msg)
                        logger.warning(f'Календарь отправлен в ТГ группе {group}')

                    calendar_counter += 1

            else:  # если нет календаря
                table_message = daily_str

                if is_exam:  # если идут экзамены, добавляем экзамен на сегодня в сообщение
                    exam_notification = get_exam_notification(group)
                    if not exam_notification:  # если на сегодня нет экзаменов, то пробуем посмотреть на завтра
                        exam_notification = get_exam_notification(group, day=date.today()+timedelta(days=1))

                    if exam_notification:
                        table_message += exam_notification

                elif is_study:  # иначе, если обычный учебный день - расписание
                    if read_table(group).split()[-1] != 'Пусто':
                        table_message += read_table(group)

                if table_message:  # если есть хоть что-то в сообщении на день, форматируем и отправляем
                    # Отправка ВК
                    if peer_id:
                        table_message = please_donate.join(table_message)  # please_donate в начало
                        response = send_message(message=table_message, peer_id=peer_id,
                                                attachment=attachment)

                        if response[0].get('conversation_message_id'):
                            pin_message(response, peer_id)  # пробуем закрепить сообщение

                        logger.warning(f'Расписание отправлено группе {group}')

                    # Отправка ТГ
                    if tg_chat:
                        if tg_last_message:
                            unpin_tg_message(tg_chat, tg_last_message)
                        msg = send_tg_message(tg_chat, table_message)
                        pin_tg_message(msg)
                        logger.warning(f'Расписание отправлено в ТГ группе {group}')

                    schedule_counter += 1

        except Exception as e:
            err_message = f'Ошибка крона в конфе {peer_id}, группа {group}: {e}\n{traceback.format_exc()}'
            send_message(err_message, 2000000001)
            send_tg_message(tg_admin_chat, err_message)

    stats_message = f'Отправлено {calendar_counter + schedule_counter} сообщений из ' \
                    f'{sum(chat_id is not None for chat_id in chat_ids)}.\n' \
                    f'Расписаний: {schedule_counter}\n' \
                    f'Календарей: {calendar_counter}'
    send_message(stats_message, 2000000001)
    send_tg_message(tg_admin_chat, stats_message)


def get_group(user_id, source='vk') -> str:  # принимает user_id и возвращает его группу
    """
    Получение номера группы пользователя

    :param int user_id: id пользователя
    :param source: vk | tg, по умолчанию vk
    :return: номер группы
    """

    id_col = 'user_id' if source == 'vk' else 'telegram_id'

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        cur.execute(f"SELECT group_id FROM user_ids WHERE {id_col}=?", [user_id])
        group = cur.fetchone()

    if group:
        group = group[0]
    else:
        return '0000'
    return group


def anekdots():
    """
    Отправка анекдотов в цикле всем подписанным
    """

    all_ids = {'vk': get_anekdot_user_ids(source='vk'),
               'tg': get_anekdot_user_ids(source='tg')}

    for source, ids in all_ids.items():
        for id in ids:
            send_message('Ежедневный анекдот:', id[0])
            for i in range(id[1]):
                send_anekdot(id[0], random.randint(0, num_of_base), target=source)


def get_custom_personal_tables_time() -> list:
    """
    Возвращает список уникальных времен отправки расписаний

    :param str source: 'vk' / 'tg' - источник сообщения
    """

    with sqlite3.connect(f'{path}admindb/databases/table_ids.db') as con:
        con.row_factory = lambda cursor, row: row[0]  # чтобы возвращать list, а не list of tuples
        cursor = con.cursor()
        res = cursor.execute(f'SELECT DISTINCT time FROM `tg_users` WHERE time IS NOT NULL').fetchall()
        res2 = cursor.execute(f'SELECT DISTINCT time FROM `vk_users` WHERE time IS NOT NULL').fetchall()
    return list(set(res + res2))


def send_personal_tables(table_time='None'):
    """
    Отправка расписаний в ЛС подписавшимся пользователям (копия обычного ежедневного расписания

    todo это можно отрефакторить - сделать единую функцию составления сообщения в беседу и пользователям,
        а тут оставить только отправку.

    :param str table_time: время отправки. 'None' - дефолтное (из конфига)
    :return: 0
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        tg_last_messages = cur.execute('SELECT telegram_id, tg_last_msg '
                                       'FROM user_ids '
                                       'WHERE tg_last_msg IS NOT NULL').fetchall()  # Чтобы откреплять сообщения в ЛС
    con.close()
    tg_last_messages = {i[0]: i[1] for i in tg_last_messages}

    day_today = date.today()
    tomorrow_weekday = get_day(day_today + timedelta(days=1))
    pin_msg = False

    # Настройка типа расписания (ежедневное/еженедельное)
    # К сожалению, фильтровать режимы расписаний на данном этапе нельзя - есть исключение в виде экзаменов
    if day_today.weekday() == 6:  # Если воскресенье, отправляем расписание на всю след. неделю + закрепляем
        day_today = f"full {get_day(date.today() + timedelta(days=1)).split()[-1]}"  # "full (parity)"
        pin_msg = True
    else:
        day_today = tomorrow_weekday

    all_ids = {'vk': get_user_table_ids(source='vk'),
               'tg': get_user_table_ids(source='tg')}

    for source, table_types_ids in all_ids.items():
        if table_time not in table_types_ids.keys():
            continue
        table_types_ids = table_types_ids[table_time]
        for table_type, ids in table_types_ids.items():
            for user_id in ids:
                group = None  # чтобы не ругался на неинициализированную переменную
                try:
                    group = get_group(user_id, source=source)
                    if group == '0000':
                        continue  # нелепый фикс непонятно чего из телеграма

                    is_exam, is_study, daily_str = daily_cron(group)  # состояние группы (семестр/сессия)

                    if is_exam and is_study:  # is_exam может =1 пораньше, для открытия расписона сессии
                        is_exam = 0
                    table_message = daily_str

                    exam_notification = None
                    if is_exam:  # если идут экзамены, добавляем экзамен на сегодня в сообщение
                        exam_notification = get_exam_notification(group, day=date.today() + timedelta(days=1))
                        if exam_notification:
                            table_message += exam_notification

                    elif is_study:  # если обычный учебный день
                        if table_type == 'daily':  # соотношение настроек пользователя и предложенного расписания
                            day_today = tomorrow_weekday
                            pin_msg = False
                        elif table_type == 'weekly' and day_today == tomorrow_weekday and not exam_notification:
                            continue  # если у пользователя только еженедельное, не отправляем ему ежедневное

                        table_message += read_table(group, day=day_today)

                    if table_message:  # если есть хоть что-то в сообщении на день
                        if table_message.split()[-1] != 'Пусто':

                            if day_today.split()[0] == 'full':
                                split_idx = table_message.find(':') + 4
                                table_message = table_message[split_idx:]

                                message = f"Расписание {group} на следующую неделю {day_today.split()[-1]}:\n" \
                                          f"{table_message}"
                            else:
                                message = f'Ежедневное расписание на завтра:\n{table_message}'

                            if source == 'tg':
                                msgg = send_tg_message(user_id, message)

                                if user_id in tg_last_messages.keys():  # открепляем предыдущее сообщение на неделю
                                    unpin_tg_message(user_id, tg_last_messages[user_id])
                                if pin_msg:  # В воскресенье закрепляем расписание на всю след. неделю
                                    pin_tg_message(msgg, chat_type='private')

                            else:
                                send_message(message, user_id)

                            logger.warning(f'Расписание отправлено юзеру {user_id} из гр. {group}')

                except Exception:
                    error_message = f'Произошла ошибка при отправке расписания: {traceback.format_exc()}\n' \
                                    f'Юзер {user_id}, группа {group}'
                    send_message(error_message, 2000000001)
                    send_tg_message(tg_admin_chat, error_message)


def check_toast():
    """
    Проверка необходимости отправки тоста

    :return: 0
    """

    now_time = datetime.today().strftime('%H:%M')

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        all_groups = cur.execute("SELECT group_id, chat_id, tg_chat_id FROM group_gcals WHERE with_toast=1").fetchall()

        for i in range(len(all_groups)):
            is_last_day, toast_time = get_last_lesson(all_groups[i][0])
            if is_last_day:
                toast_time = toast_time.strftime('%H:%M')
                if now_time == toast_time:
                    send_toast(all_groups[i][1], all_groups[i][2])

    return 0


def send_toast(chat_id, tg_chat_id=None):
    """
    Отправка тоста
    :param chat_id: id беседы
    :param tg_chat_id: id беседы в telegram
    :return: 0
    """
    toast_message = f'Еженедельный случайный тост:\n{get_random_toast(header=False)}'
    send_message(toast_message, chat_id)
    if tg_chat_id:
        send_tg_message(tg_chat_id, toast_message)
    logger.warning(f'Тост отправлен группе с peer_id={chat_id}; в telegram - {tg_chat_id}')
    return 0


def initialization():
    global vk_session
    global vk

    vk_session = vk_api.VkApi(token=token)
    vk = vk_session.get_api()

    send_message('Планировочный дед активирован', 2000000001)
    send_tg_message(-1001668185586, 'Планировочный дед активирован')
    logger.warning('Планировочный дед активирован')
    return 0


if initialization():
    logger.critical('Инициализация пошла по одному месту.')
    sys.exit()

# Тут что и когда нужно выполнять
if is_sendCron:
    schedule.every().day.at(cron_time).do(cron)

    schedule.every().day.at(tables_time).do(send_personal_tables)
    custom_table_times = get_custom_personal_tables_time()
    for custom_time in custom_table_times:
        schedule.every().day.at(custom_time).do(send_personal_tables, custom_time)

if is_sendToast:
    schedule.every().minute.do(check_toast)

schedule.every().hour.at(':20').do(load_calendar_cache)  # рандомные минуты, потому что я могу.
schedule.every(2).hours.at(':32').do(load_table_cache)  # рандомные минуты, потому что я могу.
schedule.every().day.at("07:00").do(anekdots)

try:
    while True:
        schedule.run_pending()
        time.sleep(30)
except Exception as e:
    global_err = f'Произошла ошибка при выполнении cron_table: {str(e)}\n{traceback.format_exc()}'
    send_message(global_err, 2000000001)
    send_tg_message(tg_admin_chat, global_err)
