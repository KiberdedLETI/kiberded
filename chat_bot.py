#! /usr/bin/env python
# -*- coding: utf-8 -*-
# dependencies: [chat_bot]

"""
Основная функция Чат-Бота
"""

import logging
import math
import traceback
from datetime import datetime, timedelta
import time
import pytz
import requests
import vk_api
from vk_api.utils import get_random_id
import json
import sqlite3
import threading
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import toml
import sys
import subprocess
from shiza import elements_of_shiza
from bot_functions.bots_common_funcs import read_calendar, day_of_day_toggle, read_table, get_day, weekly_toast_toggle, \
    compile_group_stats, add_user_to_table, get_exams, get_prepods, get_subjects, group_is_donator, add_user_to_anekdot, \
    get_tables_settings, set_table_mode
from bot_functions.anekdot import get_random_anekdot, get_random_toast, create_link_to_telegram
# init
logger = logging.getLogger('chat_bot')
console_handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)

try:
    config = toml.load('configuration.toml')
except FileNotFoundError:
    logger.critical('configuration.toml не найден!')
    sys.exit()

path = config.get('Kiberded').get('path')
group_token = config.get('Kiberded').get('group_token')
group_id = 0
token = config.get('Kiberded').get('token')
tg_deeplink_token = config.get('Kiberded').get('deeplink_token_key')
days = [['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'], [' (чёт)', ' (нечёт)']]
timetable = config.get('Kiberded').get('timetable')
str_day_today = get_day()

# /init


# Массивы данных для оптимизации работы бота
users = {}
# groups = {}

def update_users_data():
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()

        # достаем StudyStatus
        cur.execute("SELECT group_id, isStudy, isExam FROM group_gcals")
        status_data = {v[0]: {'isStudy':v[1], 'isExam':v[2]} for v in cur.fetchall()}
        for k, v in status_data.items():
            isStudy, isExam = v.values()
            study_status = ""
            if isExam and isStudy:
                study_status = 'mixed'
            elif isStudy:
                study_status = 'study'
            elif isExam:
                study_status = 'exam'
            status_data[v] = study_status

        # Получаем все остальные данные
        cur.execute("SELECT user_id, group_id, additional_group_id, answer_false_commands, freedom FROM user_ids")
        for row in cur.fetchall():
            user_id, group_id, additional_group_id, answer_false_commands, freedom = row

            users[user_id] = {'group': group_id,
                              'additional_group': additional_group_id,
                              'err_notifications': bool(answer_false_commands),
                              'freedom': freedom,  # Не используется - безопаснее напрямую чекать БД
                              'study_status': status_data[group_id],
                              'additional_study_status': status_data[additional_group_id]
                              }


update_users_data()


global vk
global vk_session


class DedError(Exception):
    pass


class UserGroupError(DedError):  # Ошибка когда у пользователя не определена группа
    def __init__(self, user_id, message):
        self.user_id = user_id
        self.message = message


def send_to_vk(event, keyboard_send='', message_send='Пустое сообщение', attach_send='', chat_id_send='',
               is_to_user=True):
    try:
        if is_to_user:
            user_id_send = event.obj.message["peer_id"]
        else:
            user_id_send = ''
        vk.messages.send(
            attachment=attach_send,
            keyboard=keyboard_send,
            random_id=get_random_id(),
            message=message_send,
            user_id=user_id_send,
            peer_id=chat_id_send,
            dont_parse_links=1
        )
    except vk_api.exceptions.ApiError as vk_error:
        if '[9]' in str(vk_error):  # ошибка flood-control: если флудим, то ждем секунду ответа
            logger.warning('Flood-control, спим секунду')
            time.sleep(1)
            send_to_vk(event, keyboard_send, message_send, attach_send, chat_id_send, is_to_user)
        elif '[914]' in str(vk_error):  # message is too long
            for i in range(math.floor(len(message_send)/4096)):
                send_to_vk(event, keyboard_send, message_send[i*4096:i*4096+4096], attach_send, chat_id_send, is_to_user)
            if len(message_send)%4096 != 0:
                send_to_vk(event, keyboard_send, message_send[-(len(message_send)%4096):], attach_send, chat_id_send,
                           is_to_user)
            elif attach_send:
                send_to_vk(event, keyboard_send, '', attach_send, chat_id_send, is_to_user)
        else:
            raise Exception(str(vk_error))


def get_group(user_id, message: str):
    """
    Принимает user_id и возвращает группу этого пользователя

    :param user_id: id пользователя
    :param message: для обработки ошибки DedError
    :return: номер группы
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        cur.execute("SELECT group_id FROM user_ids WHERE user_id=?", [user_id])
        group = cur.fetchone()

    if group:
        group = group[0]
    else:
        raise UserGroupError(user_id, message)
    return group


def get_additional_group(user_id):
    """
    Принимает user_id и возвращает дополнительную группу пользователя, при наличии

    :param user_id: id пользователя
    :return: номер доп. группы
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        cur.execute("SELECT additional_group_id FROM user_ids WHERE user_id=?", [user_id])
        extra_group = cur.fetchone()

    if extra_group and extra_group[0] != '':
        extra_group = extra_group[0]
    else:
        extra_group = None
    return extra_group


def group_study_status(group) -> str:
    """
    Принимает номер группы и смотрит их учебный статус, нужно для выбора открываемой клавиатуры

    :param group: номер группы
    :return: статус группы: 'mixed' (есть оба расписания) / 'study' (учебный) / 'exam' (сессия) / '' (нет расписания)
    """

    return_message = ''
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        isStudy, isExam = cur.execute("SELECT isStudy, isExam FROM group_gcals WHERE group_id=?", [group]).fetchall()[0]
        if isExam and isStudy:
            return_message = 'mixed'
        elif isStudy:
            return_message = 'study'
        elif isExam:
            return_message = 'exam'

    # если расписание уже появилось, но семестр еще не начался, открываем его todo пока не запускать
    # !!! ЕСЛИ ТУТ ЧТО-ТО ТРОНУЛ - ПОМЕНЯЙ И В telegram_bot.py!!!
    # with sqlite3.connect(f'{path}databases/{group}.db') as con:
    #     cur = con.cursor()
    #     # if cur.execute("SELECT * FROM sqlite_master WHERE name ='exam_schedule' and type='table';").fetchone():
    #     #     return 'exam' пока не буду добавлять, т.к. сессионный функционал не готов
    #     if cur.execute("SELECT * FROM sqlite_master WHERE name ='schedule' and type='table';").fetchone():
    #         return 'study'

    return return_message  # в результате получится либо keyboard_table либо keyboard_table_exam либо keyboard_table_


def open_keyboard(keyboard) -> str:
    """
    Чтение клавиатуры из .json-файла

    :param str keyboard: название клавиатуры
    :return: текст клавиатуры
    """

    with open(f'{path}keyboards/{keyboard}.json', 'r', encoding='utf-8') as f:
        result = f.read()
    return result


def get_books(subject, group_id, event, is_old=False):
    """
    Отправляет пользователю вложения, указанные в файлах в папке books

    :param str subject: предмет
    :param group_id: номер группы
    :param event: объект event от vk.api
    :param bool is_old:  if True, смотрит предмет предыдущего семестра
    """

    if is_old:
        query = f"SELECT DISTINCT " \
                f"CASE " \
                    f"WHEN doc_link IS NOT NULL OR doc_link IS NULL AND name IS NOT NULL AND file_link_tg IS NULL " \
                    f"THEN name " \
                f"END AS name, " \
                f"CASE " \
                    f"WHEN doc_link IS NOT NULL  OR doc_link IS NULL AND name IS NOT NULL AND file_link_tg IS NULL " \
                    f"THEN doc_link " \
                f"END AS doc_link FROM books_old WHERE subject=? ORDER BY name"
    else:
        query = f"SELECT DISTINCT " \
                f"CASE " \
                    f"WHEN doc_link IS NOT NULL OR doc_link IS NULL AND name IS NOT NULL AND file_link_tg IS NULL " \
                    f"THEN name " \
                f"END AS name, " \
                f"CASE " \
                    f"WHEN doc_link IS NOT NULL  OR doc_link IS NULL AND name IS NOT NULL AND file_link_tg IS NULL " \
                    f"THEN doc_link " \
                f"END AS doc_link FROM books WHERE subject=? ORDER BY name"

    with sqlite3.connect(f'{path}databases/{group_id}.db') as con:
        cur = con.cursor()
        all_books = cur.execute(query, [subject]).fetchall()
    con.close()
    if all_books:
        # первый элемент может быть null, null
        if not all_books[0][0] and not all_books[0][1]:
            all_books = all_books[1:]
        for i in range(math.ceil(len(all_books)/5)):
            message_send = ''
            attach_send = ''
            for k in range(5):
                if (i*5)+k in range(len(all_books)):
                    message_send = f'{message_send}{(i*5)+k+1}. {all_books[(i*5)+k][0]}\n'
                    attach_send = f'{attach_send}{all_books[(i * 5) + k][1]},'
            send_to_vk(message_send=message_send, attach_send=attach_send, event=event)
    else:
        send_to_vk(message_send='Пусто.\nДобавлять сюда файлы и ссылки может модератор группы.', event=event)
    return 0


def disable_err_message_notifications(user_id) -> str:
    """
    Отключение уведомлений об ошибочной команде.
    Многие пользователи любят использовать бота как беседу-архив, поэтому мы сделали такую возможность

    :param user_id: id пользователя
    :return: сообщение об отключении уведомлений
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cursor = con.cursor()
        cursor.execute(f'UPDATE user_ids SET answer_false_commands = 0 WHERE user_id = {user_id}')
    con.close()

    users[user_id]['err_notifications'] = False

    return 'Тебе больше не будут приходить сообщения об ошибочной команде.' \
           '\nЕсть вероятность, что из-за этого какие-то ошибки могут пройти незамеченными. ' \
           'Если заметишь что-то странное - можешь написать админам.' \
           '\nЕсли каким-то образом потеряешь клавиатуру, напиши "Клавиатура".'


def check_err_notification_status(user_id) -> bool:
    """
    Проверка необходимости присылать сообщение об ошибочной команде (см. disable_err_message_notifications выше)

    :param user_id: id пользователя
    :return: True - нужно отправлять сообщение, False - не нужно.
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cursor = con.cursor()
        status = cursor.execute(f'SELECT answer_false_commands FROM user_ids WHERE user_id = {user_id}').fetchone()
    con.close()
    if status is not None:
        return status[0]
    return True  # Если пользователя нет в таблице, то всегда уведомляем об ошибке команды


def get_freedom(user_id) -> str:
    """
    Получение статуса доступа пользователя
    
    :param user_id: id пользователя 
    :return: 'user'/'moderator'/'admin' - статус пользователя
    """

    freedom = 'user'
    with sqlite3.connect(f'{path}admindb/databases/admins.db') as con:
        cur = con.cursor()
        upd_freedom = cur.execute("SELECT freedom FROM users WHERE id=?", [user_id]).fetchone()
        if upd_freedom:
            freedom = upd_freedom[0]
    con.close()
    return freedom


def initialization():
    global vk
    global vk_session

    vk_session = vk_api.VkApi(token=token)
    vk = vk_session.get_api()

    send_to_vk(event=None, message_send='Кибердед активирован', chat_id_send=2000000001, is_to_user=False)
    logger.warning('Кибердед активирован')
    return 0


def main(vk_session, group_token):
    """
    Главная функция бота - тут LongPoll для работы

    :param vk_session: vk_api сессия (см. выше)
    :param group_token: токен сообщества
    """

    longpoll = VkBotLongPoll(vk_session, group_token)
    today = datetime.now(pytz.timezone('Europe/Moscow')).date()
    shiza = threading.Thread(target=elements_of_shiza.empty_thread())  # пустой поток для проверки статуса шизы
    shiza_user = ''  # пользователь шизы, для проверки статуса шизы

    message_ans = ''  # на случай какой-нибудь ошибки. Такое сообщение не отправится, т.к. есть проверка if True:

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            message = event.obj.message

            # Проверка, зарегистрирован ли пользователь
            if message['from_id'] not in users.keys():
                update_users_data()  # Повторяем проверку - вдруг мы только-только добавили пользователя
                if message['from_id'] not in users.keys():
                    raise UserGroupError(message['from_id'], message["text"])

            try:  # потому что не везде есть payload
                payload = json.loads(message["payload"])

                group = users[user_id]['group']
                additional_group = users[user_id]['additional_group']

                if payload["type"] == "navigation":  # навигация по клавиатурам

                    # endpoint-ы навигации
                    endpoint = payload["place"]

                    if endpoint == 'main':
                        kb = f'{group}_main'
                        kb_message = 'Дед на связи'

                    elif endpoint == 'table':
                        kb_message = f'Сегодня у нас: {str_day_today}'  # вызов get_day() в init
                        if additional_group:
                            if users[user_id]['additional_study_status']:  # additional только если они тоже учатся
                                kb = f'keyboard_table_{users[user_id]["study_status"]}_additional'
                            else:
                                kb = f'keyboard_table_{users[user_id]["study_status"]}'
                                kb_message += f'\nРасписание для доп. группы {additional_group} пока недоступно'
                        else:
                            kb = f'keyboard_table_{users[user_id]["study_status"]}'

                    elif endpoint == 'table_other':
                        kb = f'kb_table_other_{"even" if str_day_today.split()[1] == "(чёт)" else "odd"}'
                        kb_message = f'Если что, сегодня {str_day_today}'

                    elif endpoint == 'table_other_2':
                        kb = f'kb_table_other_{"even" if str_day_today.split()[1] == "(чёт)" else "odd"}_2'
                        kb_message = f'Расписание группы {additional_group}\nЕсли что, сегодня {str_day_today}'

                    elif endpoint == 'books':
                        if vk.groups.isMember(group_id=group_token, user_id=message["from_id"]):
                            kb = f'{group}_subjects'
                            kb_message = 'Выбирай предмет:'
                        else:
                            kb = f'{group}_main'
                            kb_message = 'Ошибка доступа - методички могут смотреть только участники сообщества'

                    elif endpoint == 'books_old':  # книжки предыдущего сема
                        if vk.groups.isMember(group_id=group_token, user_id=message["from_id"]):
                            kb = f'{group}_subjects_old'
                            kb_message = 'Выбирай предмет (предыдущий семестр):'
                        else:
                            kb = f'{group}_main'
                            kb_message = 'Ошибка доступа - методички могут смотреть только участники сообщества'

                    elif endpoint == 'prepods':
                        kb = f'{group}_prepods'
                        kb_message = 'Выбирай предмет:'

                    elif endpoint == 'prepods_old':
                        kb = f'{group}_prepods_old'
                        kb_message = 'Выбирай предмет (предыдущий семестр):'

                    elif endpoint == 'calendar':
                        kb = 'keyboard_calendar'
                        kb_message = f'Что нам готовит день грядущий? \nСегодня {today} - {str_day_today}'

                    elif endpoint == 'other':
                        kb = 'keyboard_other'
                        kb_message = 'Тут будут всякие штуки и шутки'

                    elif endpoint == 'kb_table_settings_sub':
                        kb_message = add_user_to_table(message["from_id"], '1')
                        kb = 'keyboard_table_settings'

                    elif endpoint == 'kb_table_settings_unsub':
                        kb_message = add_user_to_table(message["from_id"], '-1')
                        kb = 'keyboard_other'

                    elif endpoint == 'kb_table_settings':
                        kb_message = get_tables_settings(message["from_id"], 'vk')
                        kb = 'keyboard_table_settings'

                    elif endpoint == 'table_settings_type':
                        kb = 'keyboard_table_settings_type'
                        kb_message = 'Доступные режимы рассылки расписания:' \
                                     '\nЕжедневное - каждый день расписание на завтра (если завтра есть пары)' \
                                     '\nЕженедельное - каждое воскресенье на всю следующую неделю' \
                                     '\nОба - собственно, оба варианта.'

                    elif endpoint == 'settings':
                        kb = f'keyboard_settings_{get_freedom(message["from_id"])}'
                        if get_freedom(message["from_id"]) == 'user':
                            kb_message = f'Здесь ты можешь изменить номер своей группы. \nСейчас ты в {group}'
                        else:
                            kb_message = 'Ты можешь отредактировать бота под свою группу с помощью редактора.'

                    elif endpoint == 'donate':
                        donate_status, deadline = group_is_donator(group)
                        if donate_status and get_freedom(message["from_id"]) != 'user':
                            kb = 'keyboard_settings_donator'
                            kb_message = f'Спасибо за поддержку проекта! Здесь можно управлять функциями, ' \
                                         f'доступными группам-донатерам. Нажимай на кнопки, чтобы ' \
                                         f'включить/выключить фичу.' \
                                         f'\nДонатный функционал отключается: {deadline}' \
                                         '\nЗадонатить можно переводом на карту сбербанка: ' \
                                         '\n4274 3200 7296 2973'
                        else:
                            kb = 'keyboard_other'
                            kb_message = 'Бот живет и развивается исключительно за счет сообщества' \
                                         ' вокруг него.' \
                                         '\nЗадонатить можно переводом на карту сбербанка: ' \
                                         '\n4274 3200 7296 2973'

                    else:
                        kb = f'{group}_main'
                        kb_message = 'Ошибка навигации. \nДед на связи'
                        logger.error(f'Ошибка навигации, вызвана пэйлоадом: {payload["place"]};\n'
                                     f'Весь пэйлоад: {payload}')

                    # Ответ
                    send_to_vk(keyboard_send=open_keyboard(kb), message_send=kb_message, event=event)

                elif payload["type"] == 'action':  # команды деду, тут обращение к функциям

                    # тип действия
                    if payload["action_type"] == 'message':  # ответ сообщением (пережиток callback, зато удобно с шизой отличать)

                        command = payload["command"]

                        if command == 'table_today':
                            message_ans = read_table(group)

                        elif command == 'table_tomorrow':
                            message_ans = read_table(group, get_day(today + timedelta(days=1)))

                        elif command == 'table_weekday':
                            # if payload["weekday"] in days:  # проверка на всякий (или недостаточно?)
                            message_ans = read_table(group, payload["weekday"])

                        elif command == 'table_exam':
                            message_ans = get_exams(group)

                        elif command == 'table_today_2':
                            message_ans = f'Расписание группы {additional_group}\n' + read_table(additional_group)

                        elif command == 'table_tomorrow_2':
                            message_ans = f'Расписание группы {additional_group}\n' + \
                                          read_table(additional_group, get_day(today + timedelta(days=1)))

                        elif command == 'table_weekday_2':
                            # if payload["weekday"] in days:  # проверка на всякий (или недостаточно?)
                            message_ans = f'Расписание группы {additional_group}\n' + \
                                          read_table(additional_group, payload["weekday"])

                        elif command == 'table_exam_2':
                            message_ans = f'Расписание группы {additional_group}\n' + get_exams(additional_group)

                        elif command == 'table_empty':  # todo открывать расписание пораньше?
                            message_ans = 'Расписание на новый семестр еще не выложено, ' \
                                          'следи за апдейтами на digital.etu.ru/schedule ' \
                                          '\nРасписание в боте появляется на следующий день после выхода'

                        elif command == 'get_books':
                            message_ans = get_books(payload["subject"], group, event)

                        elif command == 'get_prepods':
                            message_ans = get_prepods(payload["subject"], group)

                        elif command == 'get_books_old':
                            message_ans = get_books(payload["subject"], group, event, is_old=True)

                        elif command == 'get_prepods_old':
                            message_ans = get_prepods(payload["subject"], group, is_old=True)

                        elif command == 'calendar_today':
                            message_ans = read_calendar(group)  # по умолчанию read_calendar(today)

                        elif command == 'calendar_tomorrow':
                            message_ans = read_calendar(group, 'tomorrow')

                        elif command == 'remove_notifications':
                            message_ans = disable_err_message_notifications(user_id=message["from_id"])

                        elif command == 'random_anecdote':
                            message_ans = get_random_anekdot()

                        elif command == 'random_toast':
                            message_ans = get_random_toast()

                        elif command == 'anecdote_subscribe':
                            message_ans = add_user_to_anekdot(message["from_id"], '1')

                        elif command == 'anecdote_unsubscribe':
                            message_ans = add_user_to_anekdot(message["from_id"], '-1')

                        elif command == 'table_set_type':
                            message_ans = set_table_mode(message["from_id"], payload["arg"], 'vk')

                        elif command == 'add_chat':
                            message_ans = 'Добавить бота в чат группы можно, ' \
                                          'нажав кнопку на странице сообщества '

                        elif command == 'link_tg':
                            if vk.groups.isMember(group_id=group_token, user_id=message["from_id"]):
                                tlink, _1, _2 = create_link_to_telegram(user_id=str(message["from_id"]),
                                                                        hash_key=tg_deeplink_token)
                                message_ans = f"Бот также есть в Telegram, твоя уникальная ссылка для авторизации:\n{tlink}"
                            else:
                                message_ans = f"Ты также можешь найти меня в Telegram: https://t.me/kiberded_leti_bot"

                        elif command == 'day_of_day_toggle':
                            message_ans = day_of_day_toggle(group)

                        elif command == 'weekly_toast_toggle':
                            message_ans = weekly_toast_toggle(group)

                        else:  # все остальное - типа обработка ошибков
                            message_ans = 'Ошибка - неизвестная команда'  # дефолтное значение
                            logger.error(f'Ошибка ответа на запрос {command};'
                                         f'\nПэйлоад: {payload}')

                        if message_ans:  # get_books возвращает 0, так что вот
                            send_to_vk(message_send=message_ans, event=event)

                    elif payload["action_type"] == 'shiza':  # шизоидные приколы
                        freedom = get_freedom(message["from_id"])  # freedom пусть остается с доступом из БД
                        shiza_message = ''
                        shiza_user = message["from_id"]

                        if payload["target"] == 'table_settings_time':
                            shiza = threading.Thread(target=elements_of_shiza.set_tables_time_vk,
                                                     args=[shiza_user])
                        elif payload["target"] == 'change_group' and freedom == 'user':
                            shiza = threading.Thread(target=elements_of_shiza.change_group_func,
                                                     args=[shiza_user])
                        elif payload["target"] == 'change_additional_group' and freedom in ('admin', 'moderator', 'user'):
                            shiza = threading.Thread(target=elements_of_shiza.change_additional_group_func,
                                                     args=[shiza_user])
                        elif payload["target"] == 'edit_database' and freedom in ('admin', 'moderator'):
                            shiza = threading.Thread(target=elements_of_shiza.shiza_main,
                                                     args=(shiza_user, freedom, 0))
                        elif payload["target"] == 'edit_admin_database' and freedom == 'admin':
                            shiza = threading.Thread(target=elements_of_shiza.shiza_main,
                                                     args=(shiza_user, freedom, 1))

                        else:  # все остальное - типа обработка ошибков
                            shiza = threading.Thread(target=elements_of_shiza.empty_thread())
                            shiza_message = f'Ошибка команды редактора: {payload["target"]}'
                            logger.error(f'Ошибка команды редактора: {payload["target"]};\n'
                                         f'Пэйлоад {payload}')

                        if shiza_message:  # если есть что сказать, так сказать
                            send_to_vk(message_send=shiza_message, event=event)
                        try:
                            shiza.start()
                        except Exception as e:
                            send_to_vk(message_send=f'Ошибка запуска редактора: {e}', event=event)
                            logger.error(f'Произошла ошибка запуска шизы {payload["target"]}: {e}')

                elif payload["type"] in ('shiza_action', 'shiza_navigation'):

                    if shiza.is_alive() and shiza_user == message["from_id"] or -group_token == message['from_id']:
                        pass  # возможно тут group_token не нужен, т.к. бот не пишет ничего пэйлоадами
                    elif message["text"] == 'Конец работы':
                        send_to_vk(message_send='Редактор уже закрыт.', event=event)
                        pass
                    else:
                        try:
                            shiza_user = message["from_id"]
                            send_to_vk(message_send='Перезапуск редактора...', event=event)
                            shiza = threading.Thread(target=elements_of_shiza.shiza_main,
                                                     args=(shiza_user, get_freedom(message["from_id"]), 0))
                            shiza.start()
                        except Exception as e:
                            send_to_vk(message_send=f'Ошибка перезапуска редактора: {e}', event=event)
                            logger.error(f'Произошла ошибка перезапуска шизы {payload["target"]}: {e}')

            # текстовые команды и в целом взаимодействие без пэйлоадов

            except KeyError:
                message_source = 'user' if message["peer_id"] < 2000000001 else 'chat'
                if message["peer_id"] == 2000000001:
                    message_source = 'admin_chat'
                message_splitted = message["text"].split()[0] + ' ' + message["text"].split()[1] if len(message["text"].split()) > 1 else message["text"]

                if shiza.is_alive() and shiza_user == message["from_id"] or -group_token == message['from_id']:
                    if message_source == 'user':  # если этот пользователь сидит в шизе и сообщение из диалога
                        continue

                # Текстовые сообщения от чата группы
                if message_source == 'chat':
                    if message_splitted in ('[club201485931|@kiberded_bot] инфо', '[club201485931|@kiberded_bot], инфо'):
                        group_stats = compile_group_stats(message["peer_id"])
                        send_to_vk(event=None, message_send=group_stats, chat_id_send=message["peer_id"], is_to_user=False)

                    elif message_splitted in ('[club201485931|@kiberded_bot] телеграм', '[club201485931|@kiberded_bot], телеграм'):

                        tg_link, _1, _2 = create_link_to_telegram(message["peer_id"], hash_key=tg_deeplink_token,
                                                                  source='group')
                        msg = f"Добавить Кибердеда в группу в Телеграме можно по ссылке: {tg_link}"
                        send_to_vk(event=None, message_send=msg, chat_id_send=message["peer_id"], is_to_user=False)

                    elif '[club201485931|@kiberded_bot]' in message["text"]:
                        send_to_vk(event=None, message_send='Неизвестная команда. Список возможных команд:\n'
                                                            '[club201485931|@kiberded_bot] инфо\n'
                                                            '[club201485931|@kiberded_bot] телеграм',
                                   chat_id_send=message["peer_id"],
                                   is_to_user=False)

                    elif message_splitted == '':  # добавление в конфу
                        add_chat_message = ''
                        new_chat_id = 2000000001
                        try:
                            if message['action']['type'] == 'chat_invite_user' and \
                                    message['action']['member_id'] == -group_token:
                                new_chat_id = message["peer_id"]
                                new_group_id = get_group(message["from_id"], message["text"])
                                add_chat_message = elements_of_shiza.add_chat(new_group_id, new_chat_id,
                                                                              get_freedom(message["from_id"]))
                                add_chat_notif = f'Добавлена конфа группы {new_group_id} ' \
                                                 f'юзером @id{message["from_id"]}\n' \
                                                 f'chat_id: {new_chat_id}\n' \
                                                 f'{" ".join(add_chat_message.split()[:4])}'  # если там ошибка
                                send_to_vk(event=None, message_send=add_chat_notif, chat_id_send=2000000001,
                                           is_to_user=False)

                        except UserGroupError as e:
                            update_users_data()  # Повторяем проверку - вдруг мы только-только добавили пользователя
                            if e.user_id not in users.keys():
                                add_chat_message = 'Ошибка добавления беседы - скорее всего у тебя не выбран номер' \
                                                   ' группы в ЛС с ботом.\n' \
                                                   'Удали меня из беседы, напиши в ЛС и потом попробуй еще раз.'
                            else:
                                add_chat_message = 'Повторная ошибка добавления беседы - id пользователя не ' \
                                                   'инициирован в боте. Просто удали меня из беседы и добавь еще раз.'

                            new_chat_id = message["peer_id"]
                            send_to_vk(event=None, message_send=f'Беседодед обосран @id{e.user_id}',
                                       chat_id_send=2000000001, is_to_user=False)

                        except KeyError:
                            pass
                        except Exception as e:
                            add_chat_message += f'Ошибка добавления беседы группы. ' \
                                                f'Попробуй еще раз или обратись к администраторам'
                            logger.error(f'Ошибка беседодеда: {e}, traceback: \n{traceback.format_exc()}')
                            send_to_vk(event=None, message_send=f'Беседодед обосран: {e}{traceback.format_exc()}',
                                       chat_id_send=2000000001, is_to_user=False)
                        if add_chat_message:
                            send_to_vk(event=None, message_send=add_chat_message, chat_id_send=new_chat_id,
                                       is_to_user=False)

                # Текстовые сообщения от админского чата
                if message_source == 'admin_chat':
                    if message_splitted in ('[club201485931|@kiberded_bot] инфо', '[club201485931|@kiberded_bot], инфо'):
                        group_stats = compile_group_stats(message["peer_id"], admin_stats=True)
                        send_to_vk(event=None, message_send=group_stats, chat_id_send=message["peer_id"], is_to_user=False)

                    elif message_splitted in ('[club201485931|@kiberded_bot] деды', '[club201485931|@kiberded_bot], деды'):
                        deds_status = subprocess.Popen(["ded", "status", "--without-color"],
                                                       stdout=subprocess.PIPE).stdout.read().decode('utf-8')
                        send_to_vk(event=None, message_send=deds_status, chat_id_send=2000000001, is_to_user=False)

                    elif message_splitted in ('[club201485931|@kiberded_bot] донатеры', '[club201485931|@kiberded_bot], донатеры'):
                        ans = 'Список донатеров:'
                        with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
                            cur = con.cursor()
                            for row in cur.execute('SELECT group_id, last_donate, with_dayofday, with_toast FROM group_gcals'):
                                if row[1]:
                                    ans += f'\n{row[0]} - до {row[1]}:\n' \
                                           f'Пикчи {"подключены" if row[2] else "отключены"}\n' \
                                           f'Тост {"подключен" if row[3] else "отключен"}\n'
                        con.close()
                        send_to_vk(event=None, message_send=ans, chat_id_send=2000000001, is_to_user=False)

                    # Рассылка сообщений через бота, вызывается только из отладочной беседы
                    elif message_splitted in ('[club201485931|@kiberded_bot] сообщение', '[club201485931|@kiberded_bot], сообщение'):
                        attachment_to_send = ''
                        if message["attachments"]:
                            attachment = message["attachments"][0]
                            if attachment["type"] == 'audio':
                                attachment = attachment["audio"]
                                attachment_to_send = f'audio{attachment["owner_id"]}_{attachment["id"]}'
                            elif attachment["type"] == 'wall':
                                attachment = attachment["wall"]
                                attachment_to_send = f'wall{attachment["from_id"]}_{attachment["id"]}'

                        message_to_send = message["text"][message["text"].find("сообщение") + 10:]  # (длина команды=9)
                        ans = subprocess.Popen(["ded", "send_message", f'attachment={attachment_to_send} ', message_to_send],
                                               stdout=subprocess.PIPE).stdout.read().decode('utf-8')
                        send_to_vk(event=None, message_send=ans, chat_id_send=2000000001, is_to_user=False)

                    elif '[club201485931|@kiberded_bot]' in message["text"]:
                        send_to_vk(event=None, chat_id_send=message["peer_id"], is_to_user=False,
                                   message_send='Неизвестная команда. Список возможных команд:\n'
                                                '[club201485931|@kiberded_bot] деды\n'
                                                '[club201485931|@kiberded_bot] телеграм\n'
                                                '[club201485931|@kiberded_bot] инфо\n'
                                                '[club201485931|@kiberded_bot] донатеры\n'
                                                '[club201485931|@kiberded_bot] сообщение '
                                                '(для справки пиши в конце ключ -h)')

                # Текстовые сообщения от пользователя
                elif message_source == 'user':
                    if message_splitted in ('Начать', 'Start'):
                        try:
                            payload = json.loads(message["payload"])
                        except KeyError:
                            if message['from_id'] not in users.keys():
                                kb_message = 'Ошибка автозапуска. Тыкни кнопку "изменить группу"'
                                send_to_vk(keyboard_send=open_keyboard('keyboard_change_group'),
                                           message_send=kb_message, event=event)
                            continue
                        if payload["command"] == "start":
                            start_message = 'Для начала, нужно настроить бота под тебя'
                            shiza = threading.Thread(target=elements_of_shiza.change_group_func,
                                                     args=[message["from_id"]])
                            send_to_vk(message_send=start_message, event=event)
                            try:
                                shiza.start()
                            except Exception as e:
                                send_to_vk(event=False, message_send=f'Ошибка стартовой шизы: {e}',
                                           chat_id_send=2000000001, is_to_user=False)
                            continue

                    elif message['from_id'] not in users.keys():
                        kb_message = 'Ошибка - нет номера группы. Тыкни кнопку "изменить группу"'
                        send_to_vk(keyboard_send=open_keyboard('keyboard_change_group'),
                                   message_send=kb_message, event=event)

                    # костыль, если пользователь потеряет клавиатуру как-то..
                    elif message_splitted in ('Клавиатура', 'клавиатура'):
                        send_to_vk(message_send='А вот и клавиатура\nДед на связи.', event=event,
                                   keyboard_send=open_keyboard(f'keyboard_other'))

                    elif users[message['from_id']]['err_notifications'] is True:
                        if len(message["text"]) == 4 and message["text"].isdecimal():
                            pass  # от шизы выбора группы
                        else:
                            send_to_vk(event, message_send='Неизвестная команда\n'
                                                           'Взаимодействуй с ботом через кнопки на всплывающей '
                                                           'клавиатуре, другие сообщения не распознаются '
                                                           '(кроме случаев, когда об этом написано).'
                                                           '\nОткрой клавиатуру кнопкой в окне диалога '
                                                           'или напиши "Клавиатура"',
                                       keyboard_send=open_keyboard('false_command_keyboard'))

        # elif event.type == VkBotEventType.MESSAGE_EVENT:  # обработка callback-кнопок в конфе
        #     if event.object.peer_id > 2000000000:
        #         match event.object.payload.get("type"):
        #             case "golos":
        #                 pass


def infinity_main():
    try:
        main(vk_session, group_token)
    except requests.exceptions.ReadTimeout:  # таймаут, который бывает раз в сутки из-за вк, примерно в час ночи
        logger.warning('Ошибка ReadTimeout')
        infinity_main()

    except requests.exceptions.ConnectionError:  # ошибка, которая иногда бывает по несколько раз в день
        logger.warning('Ошибка ConnectionError')
        infinity_main()

    except UserGroupError as e:
        if len(e.message) == 4 and e.message.isdecimal():
            infinity_main()
        else:
            update_users_data()
            if e.user_id not in users.keys():
                start_message = 'Ошибка: нет информации о группе пользователя.'
                start_kb = 'keyboard_change_group'
            else:
                start_message = 'Завершаем настройку - можешь взаимодействовать с ботом кнопками на клавиатуре:'
                start_kb = 'keyboard_other'

            send_to_vk(event=None, message_send=start_message, is_to_user=False,
                       chat_id_send=e.user_id, keyboard_send=open_keyboard(start_kb))

            infinity_main()

    except Exception as e:
        logger.error('Произошла ошибка: ' + str(e))
        try:
            error_str = f'Произошла глобальная ошибка чат-бота чатного: {str(e)}\n{traceback.format_exc()}'
            send_to_vk(event=None, message_send=error_str, chat_id_send=2000000001, is_to_user=False)
            infinity_main()
        except Exception as error_vk:
            logger.error(f'Не удалось отправить сообщение об ошибке в вк: {str(error_vk)}')
            infinity_main()


initialization()
infinity_main()
