#! /usr/bin/env python
# -*- coding: utf-8 -*-
# dependencies: [telegram_bot]

"""
Основная функция телеграмного чат-бота
todo: нужен ли group_is_donator?

"""
import math
import os
import subprocess
import time
import traceback
import telebot
from telebot import custom_filters
from telebot import types
import sqlite3
from datetime import datetime, timedelta
import pytz
from keyboards_telegram.create_keyboards import payload_to_callback, kb_prepod_schedule
from fuzzywuzzy import process
import logging
import toml
import sys
import pickle
from requests.exceptions import ReadTimeout, ConnectionError

from bot_functions.bots_common_funcs import read_calendar, read_table, get_day, \
    compile_group_stats, add_user_to_table, get_exams, get_prepods, group_is_donator, \
    add_user_to_anekdot, set_table_mode, get_tables_settings, get_donators, create_link_to_telegram
from bot_functions import attendance
from fun.anekdot import get_random_anekdot, get_random_toast
from fun.minigames import get_coin_flip_result, start_classical_rock_paper_scissors, \
    stop_classical_rock_paper_scissors, classical_rock_paper_scissors
from shiza.databases_shiza_helper import change_user_group, create_database, change_user_additional_group, \
    check_group_exists, add_donator_group


# init
logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)

try:
    config = toml.load('configuration.toml')
except FileNotFoundError:
    logger.critical('configuration.toml не найден!')
    sys.exit()

path = config.get('Kiberded').get('path')  # необходимо для корректной работы на сервере
token = config.get('Kiberded').get('token_telegram')
group_token = config.get('Kiberded').get('group_token')
tg_deeplink_token = config.get('Kiberded').get('deeplink_token_key')
days = [['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'], [' (чёт)', ' (нечёт)']]
timetable = config.get('Kiberded').get('timetable')
admin_chat = config.get('Kiberded').get('telegram_admin_chat')
books_chat = config.get('Kiberded').get('telegram_books_chat')
dayofdaypics_chat = config.get('Kiberded').get('telegram_dayofdaypics_chat')

bot = telebot.TeleBot(token)

# /init

now_date = datetime.now().strftime('%Y-%m-%d')  # необходимо для бэкапов сообщений
today = datetime.now(pytz.timezone('Europe/Moscow')).date()  # необходимо для всяких расписаний,
# с учетом перезагрузки в 00:00
list_registered_users = set()  # список зарегистрированных chat.id из group_ids.db для допуска к боту
list_unauthorized_users = set() # список зарегистрированных ТОЛЬКО в ТГ пользователей/групп
list_prepods = []  # список преподов из базы, нужно для поиска
# list_registered_groups = []  # список зарегистрированных chat.id из group_ids.db для допуска к боту
moderators = set()  # лист админов и модераторов для добавления книжек и редактирования баз
admins = set()  # лист только админов
groups = {}


class IsRegistered(custom_filters.SimpleCustomFilter):  # фильтр для проверки регистрации юзера
    key = 'is_registered'

    @staticmethod
    def check(message: telebot.types.Message, **kwargs):
        return message.chat.id in list_registered_users


class IsModerator(custom_filters.SimpleCustomFilter):  # фильтр для проверки модератора
    key = 'is_moderator'

    @staticmethod
    def check(message: telebot.types.Message, **kwargs):
        return message.chat.id in moderators


class IsAdmin(custom_filters.SimpleCustomFilter):  # фильтр для проверки админа
    key = 'is_admin'

    @staticmethod
    def check(message: telebot.types.Message, **kwargs):
        return message.chat.id in admins


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


def dump_callback(callback) -> int:  # VERY BIG Brother Is Watching You.
    """
    Фукция для дампа всех callback-ов, аналогично dump_message.
    :param callback:
    :return: 0 если все ок
    """
    date = now_date
    date_mes = callback.message.date
    chat_id = callback.message.chat.id
    message_id = callback.message.message_id  # чтобы точно задампились все сообщения, потому что могут быть удаленные и
    # отправленные несколько раз в секунду
    with open(f'{path}messages_backup/{date}/call_input_{date_mes}_{chat_id}_{message_id}.pickle', 'wb') as f:
        pickle.dump(callback, f)

    return 0


def send_message(chat_id, text, **kwargs) -> telebot.types.Message:
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


def update_list_registered_users():  # ее нужно вызывать каждый раз при запуске и добавлении юзеров
    """
    Обновляет переменную list_registered_users, загружая в нее все chat.id, которые есть в group_ids.db
    :return: 0 если все ок, иначе ошибка RuntimeError (для отправки в админскую беседу)
    """
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        con.row_factory = lambda cur, row: int(row[0])
        cur = con.cursor()
        cur.execute(f'SELECT tg_id FROM user_ids WHERE tg_id IS NOT NULL')
        users = set(cur.fetchall())

        cur.execute(f'SELECT tg_chat_id FROM group_gcals WHERE tg_chat_id IS NOT NULL')  # беседы
        groups = set(cur.fetchall())

        cur.execute(f'SELECT tg_id FROM user_ids WHERE vk_id IS NULL AND tg_id IS NOT NULL')
        unauth_users = set(cur.fetchall())
        list_unauthorized_users.update(unauth_users)

        cur.execute(f'SELECT tg_id FROM user_ids WHERE vk_id IS NOT NULL AND tg_id IS NOT NULL')
        auth_users = set(cur.fetchall())
        new_auth_users = auth_users & list_unauthorized_users  # убираем авторизовавшихся

    con.close()

    list_registered_users.update(users)
    list_registered_users.update(groups)

    for el in new_auth_users:
        list_unauthorized_users.remove(el)


def update_moderators():  # ее нужно вызывать каждый раз при запуске и добавлении модераторов
    """
        Обновляет переменную moderators, загружая в нее все chat.id, которые есть в admins.db.
        И админы, и модераторы.
        :return: 0 если все ок, иначе ошибка RuntimeError (для отправки в админскую беседу)
        """
    with sqlite3.connect(f'{path}admindb/databases/admins.db') as con:
        cur = con.cursor()
        cur.execute(f'SELECT tg_id FROM users WHERE tg_id IS NOT NULL')
        users = cur.fetchall()
    con.close()

    for user in users:
        moderators.add(int(user[0]))  # теоретически тут уязвимое место для ошибки, но либо тут добавлять
        # int, либо же в классе с фильтром добавлять str, т.к. cursor возвращает строки
    return 0


def update_admins():  # ее нужно вызывать каждый раз при запуске и добавлении админов
    """
        Обновляет переменную admins, загружая в нее все chat.id, которые есть в admins.db с freedom=admin
        И админы, и модераторы.
        :return: 0 если все ок, иначе ошибка RuntimeError (для отправки в админскую беседу)
        """
    with sqlite3.connect(f'{path}admindb/databases/admins.db') as con:
        cur = con.cursor()
        cur.execute(f'SELECT tg_id FROM users WHERE freedom=?', ['admin'])
        users = cur.fetchall()
    con.close()

    for user in users:
        admins.add(int(user[0]))  # теоретически тут уязвимое место для ошибки, но либо тут добавлять
        # int, либо же в классе с фильтром добавлять str, т.к. cursor возвращает строки
    return 0


def update_prepods():  # ее нужно вызывать каждый раз при запуске и добавлении преподов (то есть никогда лол)
    """
    Обновляет переменную list_prepods для поиска преподов

    :return: 0 если все ок
    """
    global list_prepods
    with sqlite3.connect(f'{path}admindb/databases/prepods.db') as con:
        con.row_factory = lambda cursor, row: row[0]  # чтобы возвращать list, а не list of tuples
        cur = con.cursor()
        query = 'SELECT surname FROM prepods'
        list_prepods = cur.execute(query).fetchall()
    return 0


def update_groups_data():  # ее нужно вызывать каждый раз при запуске и добавлении преподов (то есть никогда лол)
    """
    Обновляет dict с данными групп

    :return: 0 если все ок
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()

        # достаем StudyStatus
        cur.execute("SELECT group_id, isStudy, isExam, gcal_link FROM group_gcals")
        status_data = {v[0]: {'isStudy':v[1], 'isExam':v[2], 'gcal': v[3]} for v in cur.fetchall()}
        for k, v in status_data.items():
            isStudy, isExam, gcal = v.values()
            study_status = ""
            if isExam and isStudy:
                study_status = 'mixed'
            elif isStudy:
                study_status = 'study'
            elif isExam:
                study_status = 'exam'
            groups[k] = {'calendar': True if gcal else False,
                         'status': study_status}

        groups[None] = {'calendar': None,
                        'status': None}
    return 0


def callback_to_json(callback_data) -> dict:
    """
    Переводит callback_data в payload как в вк; обратная функция callback_to_json(). Сделано для удобства и красоты :)
    Подробнее см. keyboards_telegram.create_keyboards

    Пример:
    callback_data='t:action,a_t:message,c:table_empty'
    payload={"type": "action", "command": "table_empty"}
    :param callback_data: входная строка
    :return: json-dict payload
    """
    eng_to_rus_days = {
        'Monday (even)': 'Понедельник (чёт)',
        'Monday (odd)': 'Понедельник (нечёт)',
        'Tuesday (even)': 'Вторник (чёт)',
        'Tuesday (odd)': 'Вторник (нечёт)',
        'Wednesday (even)': 'Среда (чёт)',
        'Wednesday (odd)': 'Среда (нечёт)',
        'Thursday (even)': 'Четверг (чёт)',
        'Thursday (odd)': 'Четверг (нечёт)',
        'Friday (even)': 'Пятница (чёт)',
        'Friday (odd)': 'Пятница (нечёт)',
        'Saturday (even)': 'Суббота (чёт)',
        'Saturday (odd)': 'Суббота (нечёт)',
        'Sunday (even)': 'Воскресенье (чёт)',
        'Sunday (odd)': 'Воскресенье (нечёт)',
        'week (even)': 'full (чёт)',
        'week (odd)': 'full (нечёт)'
        }
    payload_item_list = ['type', 'action_type', 'command', 'place', 'weekday', 'subject', 'department_id', 'list_id']
    callback_item_list = ['t', 'a_t', 'c', 'p', 'wd', 'sj', 'did', 'lid']
    payload = {}
    for i in callback_data.split(','):
        key, value = i.split(':')
        if key in callback_item_list:
            key = payload_item_list[callback_item_list.index(key)]
        payload[key] = value
    if payload['type'] == 'action':
        if payload['command'] == 'table_weekday' \
                or payload['command'] == 'table_weekday_2' \
                or payload['command'] == 'table_prepod':
            payload['weekday'] = eng_to_rus_days[payload['weekday']]
    return payload


def get_subject_from_id(id, group):
    """
    Принимает subject_id (кусок md5-хэша) и возвращает нормальный предмет из таблицы subject_ids
    :param id: subject_id
    :param group: группа
    :return: subject
    """
    with sqlite3.connect(f'{path}databases/{group}.db') as con:
        cur = con.cursor()
        cur.execute(f'SELECT subject FROM subject_ids WHERE id=?', [id])
        subject = cur.fetchone()
    con.close()
    return subject[0]


def get_group(user_id):
    """
    Принимает user_id и возвращает группу этого пользователя.

    :param user_id: id пользователя (в таблице записан как tg_id для предотвращения путаницы с вк)
    :return: номер группы
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        cur.execute("SELECT group_id FROM user_ids WHERE tg_id=?", [user_id])
        group = cur.fetchone()

    if group:
        group = group[0]
    return group


def get_additional_group(user_id):
    """
    Принимает user_id и возвращает дополнительную группу пользователя, при наличии.
    Оставил это внутри бота пока - возможно чуть быстрее?

    :param user_id: id пользователя (в таблице записан как tg_id для предотвращения путаницы с вк)
    :return: номер доп. группы
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        cur.execute("SELECT additional_group_id FROM user_ids WHERE tg_id=?", [user_id])
        extra_group = cur.fetchone()
    if extra_group and extra_group[0] != '':
        extra_group = extra_group[0]
    else:
        extra_group = None
    return extra_group


def group_study_status(group) -> str:
    """
    Принимает номер группы и смотрит их учебный статус, нужно для выбора открываемой клавиатуры
    Оставил это внутри бота пока - возможно чуть быстрее?

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
    return return_message  # в результате получится либо kb_table либо kb_table_exam либо kb_table_


def open_keyboard(name):
    """
    Чтение клавиатуры из .json-файла

    :param str name: название клавиатуры
    :return: markup клавиатуры
    """
    with open(f'{path}keyboards_telegram/{name}.json', 'r', encoding='utf-8') as f:
        markup: telebot.types.InlineKeyboardMarkup = f.read()  # тут все нормально с типами, не верь IDE и глазам
    return markup


def get_books(subject, group, callback_object):
    """
    Отправляет пользователю вложения, указанные в файлах в папке books

    :param str subject: предмет
    :param group: группа
    :param callback_object: telebot-объект callback для изменения сообщения и для распаковки chat.id
    :return: 0 или ошибка
    """

    with sqlite3.connect(f'{path}databases/{group}.db') as con:
        cur = con.cursor()
        query = f"SELECT name, file_link_tg FROM books WHERE subject=? AND file_link_tg IS NOT NULL"
        all_books = cur.execute(query, [subject]).fetchall()
        query_links = f"SELECT name FROM books WHERE subject=? AND file_link_tg IS NULL AND doc_link IS NULL"
        all_links = cur.execute(query_links, [subject]).fetchall()
    # на всякий случай, проверка на то, не попали ли ссылки в all_books (такое мб, если not null)
    if all_books:
        i = 0
        while i < len(all_books):
            if not all_books[i][1]:
                all_links.append(all_books[i])
                all_books.remove(all_books[i])
            else:
                i += 1

    # Проверка, зарегистрирован ли пользователь ВК (только если есть методички)
    if all_books or all_links:
        if callback_object.from_user.id in list_unauthorized_users:
            err_str = f'Ошибка доступа - методички могут смотреть только авторизованные через ВК участники.' \
                      f'Это сделано для контроля доступа к файлам группы - в методички группы можно добавлять ' \
                      f'ссылки на файлы в облаке, закрытые плейлисты и пр.\n' \
                      f'Чтобы получить доступ, зарегистрируйся в сообществе ВКонтакте: https://vk.com/kiberded_bot ' \
                      f'\nВ случае возникновения сложностей можешь писать админам: ' \
                      f'https://t.me/evgeniy_setrov или https://t.me/TSheyd'
            send_message(callback_object.from_user.id, text=err_str)
            return 0

    # отдельно книжки:
    if all_books:
        for i in range(math.ceil(len(all_books)/5)):
            media = []
            for k in range(5):
                if (i*5)+k in range(len(all_books)):
                    media.append(telebot.types.InputMediaDocument(all_books[(i * 5) + k][1],
                                                                  caption=f'{(i*5)+k+1}. ' + all_books[(i*5)+k][0]))
            msg_grp = bot.send_media_group(callback_object.from_user.id, media)
            for msg in msg_grp:
                dump_message(msg)
    # и отдельно ссылки самым последним сообщением:
    if all_links:
        text = 'Ссылки:\n'
        for i in range(len(all_links)):
            text += f'{i+1}. {all_links[i][0]}\n\n'
        send_message(callback_object.from_user.id, text)
    if not all_books and not all_links:
        cl = bot.edit_message_text(f'{subject}: пусто.\nДобавлять сюда файлы и ссылки может модератор группы. '
                                   f'Изменение БД группы пока доступно только ВКонтакте.',
                              callback_object.from_user.id,
                              message_id=callback_object.message.id,
                              reply_markup=open_keyboard(f'{group}_books'))
        dump_message(cl, callback=True)
    return 0


def add_prepod_to_history(prepod_id, user_id):
    """
    Добавляет препода в историю преподов, если его там нет, или же перемещает на первое место.
    Если преподов больше 7, то удаляет последнего
    :param int prepod_id: id препода
    :param int user_id: id пользователя
    :return: 0 или ошибка
    """
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        query = f"SELECT prepod_history FROM user_ids WHERE tg_id=?"
        prepod_history = cur.execute(query, [user_id]).fetchone()[0]
        if prepod_history:
            prepod_history = prepod_history.split(',')
            if prepod_id in prepod_history:
                prepod_history.remove(prepod_id)
            prepod_history.insert(0, prepod_id)
            if len(prepod_history) > 7:
                prepod_history.pop()
            prepod_history = ','.join(prepod_history)
        else:
            prepod_history = str(prepod_id)
        query = f"UPDATE user_ids SET prepod_history=? WHERE tg_id=?"
        cur.execute(query, [prepod_history, user_id])
        con.commit()
    return 0


def get_prepod_info(prepod_id):
    """
    Получает информацию о преподе из БД
    :param int prepod_id: id препода
    :return: кортеж с информацией [id, department_id, initials, name, surname, midname, roles], название кафедры
    """

    with sqlite3.connect(f'{path}admindb/databases/prepods.db') as con:
        cur = con.cursor()
        query = f"SELECT * FROM prepods WHERE id=?"
        prepod_info = cur.execute(query, [prepod_id]).fetchall()
        readable_department = ""
        # todo убрать это вообще - все норм в базе будет.
        if prepod_info:
            departments = [str(e[1]) for e in prepod_info]
            prepod_info = prepod_info[0]

            query = "SELECT title FROM departments WHERE id IN ({})".format(','.join(departments))
            readable_department = ', '.join([e[0] for e in cur.execute(query).fetchall()])
        return prepod_info, readable_department


def get_prepods_history(call):
    """
    Получает историю преподов пользователя и отправляет ему кнопки с ними
    :param call: callback-объект для изменения сообщения
    :return: список преподов
    """
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        query = f"SELECT prepod_history FROM user_ids WHERE tg_id=?"
        prepod_history = cur.execute(query, [call.from_user.id]).fetchone()[0]
        if prepod_history:
            prepod_history = prepod_history.split(',')
            prepod_history = [int(i) for i in prepod_history]
        else:
            prepod_history = []
    if prepod_history:
        markup = telebot.types.InlineKeyboardMarkup()
        for prepod_id in prepod_history:
            prepod, department = get_prepod_info(prepod_id)
            payload = {"type": "action",
                       "command": f"choose_prepod",
                       "id": str(prepod[0]),
                       "department_id": str(prepod[1])
                       }
            callback = payload_to_callback(payload)
            markup.add(telebot.types.InlineKeyboardButton(text=f'{prepod[2]} ({department})',
                                                          callback_data=callback))
        payload = {"type": "navigation",
                   "place": "table_prepods"}
        callback = payload_to_callback(payload)
        markup.add(telebot.types.InlineKeyboardButton(text=f'Назад', callback_data=callback))
        cl = bot.edit_message_text(text='Выбери препода из истории:',
                                   chat_id=call.from_user.id,
                                   message_id=call.message.id,
                                   reply_markup=markup)
        dump_message(cl, callback=True)
    else:
        markup = telebot.types.InlineKeyboardMarkup()
        payload = {"type": "navigation",
                   "place": "table_prepods"}
        callback = payload_to_callback(payload)
        markup.add(telebot.types.InlineKeyboardButton(text=f'Назад', callback_data=callback))
        cl = bot.edit_message_text(chat_id=call.from_user.id,
                                   text='История пуста.',
                                   message_id=call.message.id,
                                   reply_markup=markup)
        dump_message(cl, callback=True)
    return prepod_history


def get_prepod_schedule(prepod_id, weekday):
    """
    Получает расписание препода из БД
    :param int prepod_id: id препода
    :param int weekday: номер дня недели
    :return: расписание препода
    """
    with sqlite3.connect(f'{path}admindb/databases/prepods.db') as con:
        cur = con.cursor()
        query = f"SELECT day_table FROM table_cache WHERE id=? AND day=?"
        schedule = cur.execute(query, [prepod_id, weekday]).fetchall()
    if schedule:
        schedule = schedule[0]
    else:
        schedule = 'У преподавателя пока нет расписания на этот семестр.'
    return schedule


def set_tables_time(message):
    """
    Настройка подписки на расписания (время рассылки)
    """

    time_ = str(message.text)
    if len(time_) != 5:  # Дополняем нулями, если необходимо
        time_ = time_.zfill(5)

    try:  # Проверка формата времени
        time_check = time.strptime(time_, '%H:%M')
    except ValueError:
        msg = 'Ошибка - проверь формат сообщения (ЧЧ:ММ), нажми кнопку и попробуй еще раз'
        send_message(message.chat.id, msg)
        return False

    with sqlite3.connect(f'{path}admindb/databases/table_ids.db') as con:
        cur = con.cursor()
        upd_query = f'UPDATE `tg_users` SET time=? WHERE id=?'
        cur.execute(upd_query, (time_, message.chat.id))
        con.commit()

    msg = f'Время рассылки расписания установлено: {time_}. Изменения вступят в силу со следующего дня'
    send_message(message.chat.id, msg)
    return True


# Команды в ЛС:
@bot.message_handler(commands=['main'], is_registered=True)
def main_reply(message):
    dump_message(message)

    if message.chat.type == 'private':
        group = get_group(message.chat.id)
        markup = open_keyboard(f'{group}_main')
        send_message(message.chat.id, "Дед на связи", reply_markup=markup)
    else:
        send_message(message.chat.id, "Данная команда доступна только в личных сообщениях.")


@bot.message_handler(commands=['change_group'], is_registered=True)
def change_group(message):
    dump_message(message)

    if message.chat.type == 'private':

        group = get_group(message.chat.id)
        additional_group = get_additional_group(message.chat.id)

        if message.chat.id in moderators:
            kb = open_keyboard('kb_change_additional_group')
            send_message(message.chat.id,
                         f'Текущая группа: {group}.\n Текущая доп.группа: {additional_group}.\n'
                         'Для изменения дополнительной группы нажми на кнопку ниже.\n'
                         'Изменение основной группы недоступно модераторам. При необходимости напиши админам: '
                         'https://t.me/evgeniy_setrov или https://t.me/TSheyd', reply_markup=kb,
                         disable_web_page_preview=True)

        else:
            kb = open_keyboard('kb_change_groups')
            send_message(message.chat.id,
                         f'Текущая группа: {group}.\n Текущая доп.группа: {additional_group}.\n'
                         'Для изменения нажми на одну из кнопок ниже:', reply_markup=kb)

    else:
        send_message(message.chat.id, "Данная команда доступна только в личных сообщениях.")


def change_group_step(message):
    dump_message(message)

    group = get_group(message.chat.id)

    if len(message.text) == 4 and message.text.isdecimal():

        if not check_group_exists(message.text):
            send_message(message.chat.id, f'Ошибка - группа {message.text} не найдена. '
                                          f'Проверь правильность номера или обратись к администраторам')
            return False

        group_exists, user_existed, msg = change_user_group(message.text, message.chat.id, source='telegram')

        if not group_exists:
            add_db_response, admin_add_db_response = create_database(message.text)
            send_message(admin_chat, text=admin_add_db_response)
            send_message(message.chat.id, text=add_db_response)
        markup = open_keyboard(f'{message.text}_main')
        send_message(message.chat.id, text=msg, reply_markup=markup)

        if group is None:
            admin_msg = f'К нам пришел дикий {message.chat.id} (@{message.from_user.username}) из {message.text}'
        else:
            admin_msg = f'Юзер {message.chat.id} (@{message.from_user.username}) изменил группу: ' \
                        f'{group} -> {message.text}'

        send_message(admin_chat, admin_msg)

    else:
        msg = 'Ошибка - неверный формат номера группы'
        send_message(message.chat.id, msg)
    update_list_registered_users()


def change_additional_group_step(message):
    dump_message(message)

    additional_group = get_additional_group(message.chat.id)

    if len(message.text) == 4 and message.text.isdecimal():

        if str(message.text) != '0000':
            if not check_group_exists(message.text):
                send_message(message.chat.id, f'Ошибка - группа {message.text} не найдена. '
                                              f'Проверь правильность номера или обратись к администраторам')
                return False

        user_existed, msg = change_user_additional_group(message.text, message.chat.id, source='telegram')

        send_message(message.chat.id, text=msg)
        if not additional_group:
            send_message(admin_chat, f'Юзер {message.chat.id} (@{message.from_user.username}) добавил доп. группу: '
                                     f'{message.text}')
        elif message.text == '0000':
            send_message(admin_chat, f'Юзер {message.chat.id} (@{message.from_user.username}) удалил доп. группу.')
        else:
            send_message(admin_chat, f'Юзер {message.chat.id} (@{message.from_user.username}) изменил доп. группу: '
                                     f'{additional_group if additional_group else "None"} -> {message.text}')

    else:
        msg = 'Ошибка - неверный формат номера группы'
        send_message(message.chat.id, msg)


def add_new_chat_step(message):
    group = str(message.text)
    tg_id = message.chat.id

    if len(group) != 4 or not group.isdecimal():
        send_message(tg_id, f'Ошибка - неверный формат номера группы: {group}. Попробуй еще раз')
        return 0
    
    return_str = ''
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()

        group_check = cur.execute('SELECT group_id FROM group_gcals WHERE group_id=?', [group]).fetchone()
        if not group_check:
            send_message(tg_id, f'Ошибка - нет такой группы: {group}. Проверь данные и попробуй еще раз')
            return 0

        old_chat_id = cur.execute('SELECT vk_chat_id FROM group_gcals WHERE group_id=?', [group]).fetchone()[0]
        if old_chat_id:
            return_str = f'Беседа группы {group} уже есть ВКонтакте - vk_chat_id={old_chat_id}\n' \
                         f'Чтобы добавить беседу и в Телеграм, напиши в беседе ВК команду "@kiberded_bot телеграм"'
        else:
            old_chat_id = cur.execute('SELECT tg_chat_id '
                                      'FROM group_gcals '
                                      'WHERE group_id=?', [group]).fetchone()[0]
            if old_chat_id:
                if tg_id == old_chat_id:
                    send_message(tg_id, f'Беседа уже привязана к группе {group}')
                send_message(tg_id, f'Беседа {group} уже существует, создание нескольких бесед на группу пока '
                                    f'не поддерживается')
                return 0

            cur.execute('UPDATE group_gcals SET tg_chat_id=NULL WHERE tg_chat_id=?', [tg_id])
            cur.execute('UPDATE group_gcals SET tg_chat_id=? WHERE group_id=?', [tg_id, group])
            con.commit()
            return_str = f'Группа {group} успешно добавлена.\n' \
                         f'Теперь бот будет ежедневно утром присылать сюда расписание на день. Расписание ' \
                         f'создается на основе расписания на сайта ЛЭТИ и может изменяться модератором ' \
                         f'группы.\n' \
                         f'Также Кибердед может присылать ' \
                         f'уведомления о новых письмах на почте группы (если подключить почту). ' \
                         f'Вместо расписания бот может присылать ивенты на день с ' \
                         f'гугл-календаря (при наличии).' \
                         f'\nВсе настройки бота под группу доступны пока только ВКонтакте: https://vk.com/kiberded_bot'
    con.close()

    update_list_registered_users()

    send_message(tg_id, return_str)
    send_message(admin_chat, f'К нам пришла дикая конфа {group}: {message.chat.id}, '
                             f'username: @{message.from_user.username}')

    return 0


def search_prepods_by_surname(surname):
    """
    Поиск id преподавателей по фамилии
    :param surname: фамилия преподавателя
    :return: [prepodId, departmentId] - список id преподавателей/кафедр
    """
    with sqlite3.connect(f'{path}admindb/databases/prepods.db') as con:
        con.row_factory = lambda cursor, row: row[0]  # чтобы возвращать list, а не list of tuples
        cur = con.cursor()
        prepods = cur.execute('SELECT id, department_id FROM prepods WHERE surname=?', [surname]).fetchall()
    con.close()
    return prepods


def search_prepod_text_step(message):
    """
    Поиск преподов в списке list_prepods и отправка юзеру кнопочек
    :param message:
    :return: 0
    """
    dump_message(message)

    result = process.extract(message.text, list_prepods, limit=4)
    if result[0][1] == 100:
        answer = 'Преподаватель найден'
        markup = telebot.types.InlineKeyboardMarkup()
        prepods = search_prepods_by_surname(result[0][0])
        for prepod_id in prepods:
            prepod, department = get_prepod_info(prepod_id)
            payload = {"type": "action",
                       "command": f"choose_prepod",
                       "id": str(prepod[0]),
                       "department_id": str(prepod[1])
                       }
            callback = payload_to_callback(payload)
            markup.add(telebot.types.InlineKeyboardButton(text=f'{prepod[2]} ({department})',
                                                          callback_data=callback))
        payload = {"type": "navigation",
                   "place": "table_prepods"}
        callback = payload_to_callback(payload)
        markup.add(telebot.types.InlineKeyboardButton(text=f'Назад', callback_data=callback))
    else:
        answer = 'Точных совпадений не найдено. Похожие фамилии:'
        markup = telebot.types.InlineKeyboardMarkup()
        for element in result:
            prepods = search_prepods_by_surname(element[0])
            for prepod_id in prepods:
                prepod, department = get_prepod_info(prepod_id)
                payload = {"type": "action",
                           "command": f"choose_prepod",
                           "id": str(prepod[0]),
                           "department_id": str(prepod[1])
                           }
                callback = payload_to_callback(payload)
                markup.add(telebot.types.InlineKeyboardButton(text=f'{prepod[2]} ({department})',
                                                              callback_data=callback))
        payload = {"type": "navigation",
                   "place": "table_prepods"}
        callback = payload_to_callback(payload)
        markup.add(telebot.types.InlineKeyboardButton(text=f'Назад', callback_data=callback))
    send_message(chat_id=message.chat.id, text=answer, reply_markup=markup)


def add_telegram_user_id(vk_id, tg_id, id_type='user'):
    """
    Добавление аккаунта пользователя в Телеграме к строке с его аккаунтом в ВК. Здесь нет обработки каких-то ошибок,
    т.к. наличие строки с айди ВК предусмотрено авторизацией по хэшу

    :param vk_id: айди пользователя/беседы ВК
    :param tg_id: айди пользователя/беседы ТГ
    :param id_type: тип айди - "user" или "group"
    :return: Сообщение о привязке аккаунта, группа пользователя
    """

    if id_type == 'user':
        del_q = f'DELETE FROM user_ids WHERE tg_id=? AND vk_id IS NULL'
        old_q = f'SELECT tg_id FROM user_ids WHERE vk_id=?'
        upd_q = f'UPDATE user_ids SET tg_id=? WHERE vk_id=?'
        grp_q = f'SELECT group_id FROM user_ids WHERE vk_id=?'
        grp_alt_q = f'SELECT group_id FROM user_ids WHERE tg_id=?'
    elif id_type == 'group':
        del_q = f'DELETE FROM group_gcals WHERE tg_chat_id=? AND vk_chat_id IS NULL'
        old_q = f'SELECT tg_chat_id FROM group_gcals WHERE vk_chat_id=?'
        upd_q = f'UPDATE group_gcals SET tg_chat_id=? WHERE vk_chat_id=?'
        grp_q = f'SELECT group_id FROM group_gcals WHERE vk_chat_id=?'
        grp_alt_q = f'SELECT group_id FROM group_gcals WHERE tg_chat_id=?'  # вот этот запрос пока не нужен, но все же
    else:
        raise ValueError('id_type must be "user" or "group"')

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()

        group = cur.execute(grp_q, [vk_id]).fetchone()
        if not group:  # неавторизованный пользователь регистрируется
            group = cur.execute(grp_alt_q, [tg_id]).fetchone()
        group = group[0]

        old_id = cur.execute(old_q, [vk_id]).fetchone()  # Проверяем, не привязан ли аккаунт уже.
        if old_id:
            if old_id[0] == tg_id:
                msg = f'Аккаунт уже привязан к https://vk.com/id{vk_id} ({group})' if id_type == 'user' \
                    else f'Беседа уже привязана к {group}'
                return msg, group

        # Если что-то было зарегистрировано в ТГ, но не в ВК - удаляем строку и перезаписываем в строке в ВК
        cur.execute(del_q, [tg_id])

        # Случай регистрации пользователя без ВК обрабатывается change_group_step

        cur.execute(upd_q, (tg_id, vk_id))
        con.commit()
    con.close()

    update_list_registered_users()

    if id_type == 'user':
        return f"Аккаунт в Телеграме успешно привязан к https://vk.com/id{vk_id}, группа {group}.", group

    elif id_type == 'group':
        return f"Группа в Телеграме успешно привязана к vk_chat_id={vk_id}, группа {group}.", group


def get_attendance_statistics_today(checkin):
    """
    Формирует адекватный строковый ответ о статистике посещаемости за сегодня из ответа с
    https://digital.etu.ru/attendance/api/schedule/check-in

    :param checkin: json ответ
    :return str: ответ в виде строки
    """
    answer = 'Статистика за сегодня: \n\n'
    for lesson_elem in checkin:
        time_start = time.strptime(lesson_elem['start'], '%Y-%m-%dT%H:%M:%S.000%z')
        time_end = time.strptime(lesson_elem['end'], '%Y-%m-%dT%H:%M:%S.000%z')
        day_class = time_start.tm_yday
        day_now = time.gmtime(time.time()).tm_yday

        if day_now == day_class:
            lesson_name = lesson_elem['lesson']['shortTitle']
            subject_type = lesson_elem['lesson']['subjectType']
            self_reported = lesson_elem['selfReported']

            if self_reported:
                self_reported_ans = '✅'
            elif self_reported == False:  # не надо делать elif not self_reported, т.к. в случае отсутствия отметки
                # сработает это условие (тип Nonetype), а по моей логике должно сработать условие else
                self_reported_ans = '❌'
            else:
                self_reported_ans = '🟢'

            answer += f'{time_start.tm_hour:02}:{time_start.tm_min:02} - {time_end.tm_hour:02}:{time_end.tm_min:02}: ' \
                      f'{lesson_name} ({subject_type}): {self_reported_ans}\n'
    return answer


def check_in_at_lesson(chat_id, lesson_id):
    """
    Функция для отмечания на паре

    """
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        data = cur.execute("SELECT lk_email, lk_password FROM user_ids WHERE tg_id=?", [chat_id]).fetchall()
        data = list(data[0])

    msg = send_message(chat_id, 'Отмечаемся на паре... Логинюсь в ЛК...')
    session = attendance.start_new_session()
    code, session = attendance.auth_in_lk(session, data[0], data[1])
    if code == 200:
        msg = bot.edit_message_text(msg.text + '✅\nЛогинюсь в ИС Посещаемость...', msg.chat.id, msg.id)
    else:
        bot.edit_message_text(f'Аутентификация в ЛК не удалась. Возможно в базе хранятся неправильные данные для входа.'
                              f'\nТекущие данные:\n\nemail: {data[0]}\nПароль: ***{data[1][:-3]}. \n\nЕсли данные'
                              f'верны, попробуй еще раз.', msg.chat.id, msg.id)
        return 0
    code, session = attendance.auth_in_attendance(session)
    if code == 200:
        msg = bot.edit_message_text(msg.text + '✅\nОтмечаюсь на паре...', msg.chat.id, msg.id)
    else:
        bot.edit_message_text(f'Аутентификация в ИС Посещаемость не удалась.', msg.chat.id, msg.id)
        return 0
    code, session = attendance.check_in_at_lesson(session, lesson_id)
    if code == 201:
        msg = bot.edit_message_text(msg.text + '✅\nТы успешно отметился на паре.\n\n', msg.chat.id, msg.id)
    else:
        bot.edit_message_text(f'Отметиться на паре не удалось. Возможно, время уже вышло. Код ошибки: {code}',
                              msg.chat.id, msg.id)
        return 0
    code, time_data, user, checkin, alldata = attendance.get_info_from_attendance(session)

    answer = get_attendance_statistics_today(checkin)

    if code == 200:
        msg = bot.edit_message_text(msg.text + answer, msg.chat.id, msg.id)
    else:
        msg = bot.edit_message_text(msg.text + 'Не удалось загрузить статистику о сегодняшних отметках. Попробуй еще раз '
                                         'через /attendance_stat или вручную.', msg.chat.id, msg.id)
    return 0


@bot.message_handler(commands=['start'])
def send_welcome(message):
    dump_message(message)

    # Достаем код ('/start unique_code')
    unique_code = message.text.split()[1] if len(message.text.split()) > 1 else None

    if unique_code is not None and '_' in unique_code:  # if the '/start' command contains a unique_code
        # Сравниваем хэш из ссылки с локально сгенерированным по user_id
        user_id, user_hash = unique_code.split('_')
        dummy_link, _, server_hash = create_link_to_telegram(str(user_id), hash_key=tg_deeplink_token)
        logger.info(f"[Auth] - vk_id: {user_id}, tg_id: {message.chat.id}, "
                    f"user_hash: {user_hash}, server_hash: {server_hash}")

        if server_hash == user_hash:  # Совпадает - добавляем пользователя/беседу
            if int(user_id) > 2000000000:  # источник сообщения - беседа todo если нет беседы вк, предлагать добавить в телеге
                reply, user_group = add_telegram_user_id(str(user_id), str(message.chat.id), id_type='group')
                msg_source = 'vk_chat_id='

            else:  # источник сообщения - пользователь
                reply, user_group = add_telegram_user_id(str(user_id), str(message.chat.id))
                msg_source = 'https://vk.com/id'

            send_message(admin_chat, f'{msg_source}{user_id} из {user_group} пришел в Telegram, '
                                     f'chat.id: {message.chat.id}, username: @{message.from_user.username}')
            send_message(message.chat.id, reply)
            return 0
        else:
            send_message(admin_chat, f'Попытка авторизации с неверным хэшем: {user_id}, '
                                     f'username: @{message.from_user.username}')
            send_message(message.chat.id, 'Неверный код авторизации, регистрация вручную...')

    # Регистрация без ВК
    msg = send_message(message.chat.id, 'Введи номер группы в формате ХХХХ, например 9281\n'
                                        '(P.S. Бот не видит сообщений без прав администратора)')

    if message.chat.type != 'private':
        bot.register_next_step_handler(msg, add_new_chat_step)
    elif message.chat.type == 'private':
        bot.register_next_step_handler(msg, change_group_step)


@bot.message_handler(commands=['info', 'инфо'], is_registered=True)
def info_about_group(message):
    dump_message(message)

    if message.chat.type in ['group', 'supergroup']:
        group_stats = compile_group_stats(message.chat.id, admin_stats=True if message.chat.id == admin_chat else False,
                                          source='tg')
        send_message(message.chat.id, group_stats)
    else:
        send_message(message.chat.id, 'Данная команда доступна только в беседах (groups & supergroups).')


@bot.message_handler(commands=['help'], chat_types='private', is_registered=True)  # на случай команды help из лс todo
def help_private(message):
    dump_message(message)
    if message.chat.id in admins:
        answer = 'Ты админ, тебе доступны команды, которых нет в меню. Вот список всех доступных:' \
                 '\n/main - кнопка на случай, если вдруг куда-то пропала основная нижняя клавиатура' \
                 '\n/auth - авторизация через ВКонтакте, для доступа к методичкам и синхронизации настроек' \
                 '\n/help - справка, ты здесь' \
                 '\n/set_lk_secrets - установка логина и пароля от личного кабинета ЛЭТИ' \
                 '\n/add_book - добавление книг' \
                 '\n/add_moderator - добавить модератора' \
                 '\n/add_dayofday_picture - добавление пикчи дня дня в общую базу картиночек' \
                 '\nЧтобы добавить бота в беседу, напиши "/start@kiberded_bot_leti" в чате после добавления' \
                 '\n\nОбщая справка по боту: будет позже'
    elif message.chat.id in moderators:
        answer = 'Ты модератор, тебе доступны команды, которых нет в меню. Вот список всех доступных:' \
                 '\n/main - кнопка на случай, если вдруг куда-то пропала основная нижняя клавиатура' \
                 '\n/auth - авторизация через ВКонтакте, для доступа к методичкам и синхронизации настроек' \
                 '\n/help - справка, ты здесь' \
                 '\n/set_lk_secrets - установка логина и пароля от личного кабинета ЛЭТИ' \
                 '\n/add_book - добавление книг' \
                 '\nЧтобы добавить бота в беседу, напиши "/start@kiberded_bot_leti" в чате после добавления' \
                 '\n\nОбщая справка по боту: будет позже'
    else:
        answer = 'Список доступных команд:' \
                 '\n/main - кнопка на случай, если вдруг куда-то пропала основная нижняя клавиатура' \
                 '\n/auth - авторизация через ВКонтакте, для доступа к методичкам и синхронизации настроек' \
                 '\n/change_group - изменить группу' \
                 '\n/help - справка, ты здесь' \
                 '\n/set_lk_secrets - установка логина и пароля от личного кабинета ЛЭТИ' \
                 '\nЧтобы добавить бота в беседу, напиши "/start@kiberded_bot_leti" в чате после добавления' \
                 '\n\nОбщая справка под боту: будет позже'
    send_message(message.chat.id, answer)


@bot.message_handler(commands=['auth'], chat_types='private', is_registered=True)
def auth_message(message):
    dump_message(message)
    send_message(message.chat.id, 'Чтобы авторизоваться в боте, зайди в раздел "Прочее" в боте '
                                  f'[ВКонтакте](https://vk.com/im?sel=-{group_token}) и перейди по ссылке с кнопки '
                                  '"Телеграм"')


@bot.message_handler(commands=['minigames'], chat_types='private', is_registered=True)
def minigames(message):
    dump_message(message)

    markup = open_keyboard('kb_minigames')
    send_message(message.chat.id, 'Выбери игру', reply_markup=markup)


@bot.message_handler(commands=['set_lk_secrets'], chat_types='private', is_registered=True)
def set_lk_secrets(message):
    dump_message(message)

    markup = open_keyboard('kb_cancel_set_lk_secrets')
    msg = send_message(message.chat.id, 'Ты попал в меню установки логина и пароля от личного кабинета ЛЭТИ.\n\n'
                                        'На данный момент ведется разработка интеграции с системой посещаемости, '
                                        'благодаря чему (может быть) можно будет отмечаться на парах прямо из деда. '
                                        '\n\nВНИМАНИЕ! Данные от личного кабинета хранятся на собственных серверах'
                                        'в НЕзашифрованном виде, и вообще, использование этого сервиса происходит'
                                        'на условиях "как есть", и мы не несем никакой ответственности в случае'
                                        'каких-либо сливов.\n\nВведи на первой строке электронную почту (логин от ЛК),'
                                        'на второй - пароль, например: \n\nexample@example.com\n'
                                        'thisissuperstrongpassword\n\n или нажми на кнопку отмены.', reply_markup=markup)
    bot.register_next_step_handler(msg, set_lk_secrets_next_step)


def set_lk_secrets_next_step(message):  # обработка ввода данных от лк
    dump_message(message)

    vec = message.text.split('\n')
    if len(vec) == 2:
        email = vec[0]
        password = vec[1]
    else:
        send_message(message.chat.id, 'Необходимо ввести на первой строке email, на второй - пароль. Попробуй запустить'
                                      'меню установки заново.')
        return 0
    msg = send_message(message.chat.id, 'Попытка войти в ЛК с переданными данными....')
    code, session = attendance.auth_in_lk(attendance.start_new_session(), email, password)
    if code == 200:
        msg = bot.edit_message_text(msg.text + f'\nУспешно! \n\nЗапись данных в базу...', message.chat.id, msg.id)
    else:
        msg = bot.edit_message_text(msg.text + f'\nАутентификация в ЛК не удалась. Попробуй еще раз и проверь '
                                               f'введенные данные.', message.chat.id, msg.id)
        return 0
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        cur.execute("UPDATE user_ids SET lk_email=?, lk_password=? WHERE tg_id=?", (email, password, message.chat.id))

    msg = bot.edit_message_text(msg.text + f'\nДанные успешно записаны.', message.chat.id, msg.id)


@bot.message_handler(commands=['attendance_stat'], chat_types='private', is_registered=True)  # временно, для отладки
def attendance_stat(message):
    dump_message(message)
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        data = cur.execute("SELECT lk_email, lk_password FROM user_ids WHERE tg_id=?", [message.chat.id]).fetchall()
        data = list(data[0])

    msg = send_message(message.chat.id, 'Логинюсь в ЛК...')
    session = attendance.start_new_session()
    code, session = attendance.auth_in_lk(session, data[0], data[1])
    if code == 200:
        msg = bot.edit_message_text(msg.text + '✅\nЛогинюсь в ИС Посещаемость...', msg.chat.id, msg.id)
    else:
        bot.edit_message_text(f'Аутентификация в ЛК не удалась. Возможно в базе хранятся неправильные данные для входа.'
                              f'\nТекущие данные:\n\nemail: {data[0]}\nПароль: ***{data[1][:-3]}. \n\nЕсли данные'
                              f'верны, попробуй еще раз.', msg.chat.id, msg.id)
        return 0
    code, session = attendance.auth_in_attendance(session)
    if code == 200:
        msg = bot.edit_message_text(msg.text + '✅\nЗагружаю статистику за день...', msg.chat.id, msg.id)
    else:
        bot.edit_message_text(f'Аутентификация в ИС Посещаемость не удалась.', msg.chat.id, msg.id)
        return 0
    code, time_data, user, checkin, alldata = attendance.get_info_from_attendance(session)

    answer = get_attendance_statistics_today(checkin)

    if code == 200:
        msg = bot.edit_message_text(answer, msg.chat.id, msg.id)
    else:
        bot.edit_message_text('Не удалось загрузить статистику о сегодняшних отметках.', msg.chat.id, msg.id)


# Команды для модераторов:
@bot.message_handler(commands=['add_book'], is_moderator=True)
def add_book(message):
    dump_message(message)

    msg = send_message(message.chat.id, 'Отправь нужный файл. Перед отправкой убедись, что он нормально назван')
    bot.register_next_step_handler(msg, add_book_next_step)


def add_book_next_step(message):  # обработка добавления книжки
    dump_message(message)

    try:
        with sqlite3.connect(f'{path}admindb/databases/admins.db') as con:
            cur = con.cursor()
            cur.execute("SELECT group_id FROM users WHERE tg_id=?", [message.chat.id])
            group = cur.fetchone()[0]
    except:
        group = 'ERROR'

    if message.content_type == 'document':
        send_message(message.chat.id, f'Успешно. file_id документа:\n\n{message.document.file_id}\n\n'
                                      f'Используй его для редактирования базы через /edit_db.\n\n'
                                      f'Проверки ради сообщением ниже я скину эту же книгу, проверь что все ок:')
        bot.send_document(message.chat.id, message.document.file_id)
        send_message(books_chat, f'Юзер {message.chat.id} (@{message.from_user.username}) из группы {group} '
                                 f'добавил книгу: \n{message.document.file_name}\n'
                                 f'\nfile_id:{message.document.file_id}')
        bot.send_document(books_chat, message.document.file_id)
    else:
        send_message(message.chat.id, f'Ошибка: ожидался файл, а мне пришло: {message.content_type}')
        send_message(books_chat, f'Юзер {message.chat.id} (@{message.from_user.username}) из группы {group} '
                                 f'пытался скинуть книгу, а скинул фигу: {message.content_type}'
                                 f'\nПодробнее можно глянуть в огурчиках: '
                                 f'{message.date}_{message.chat.id}_{message.id}.pickle')


# Команды для админов:
@bot.message_handler(commands=['add_dayofday_picture'], is_admin=True)
def add_dayofday_picture(message):
    dump_message(message)
    print(message)

    msg = send_message(message.chat.id, 'Отправь картинку')
    bot.register_next_step_handler(msg, add_dayofday_picture_next_step)


def add_dayofday_picture_next_step(message):  # обработка добавления картиночки дня дня
    dump_message(message)

    try:
        with sqlite3.connect(f'{path}admindb/databases/admins.db') as con:
            cur = con.cursor()
            cur.execute("SELECT group_id FROM users WHERE tg_id=?", [message.chat.id])
            group = cur.fetchone()[0]
    except:
        group = 'ERROR'

    if message.content_type == 'photo':
        send_message(message.chat.id, f'Успешно. file_id документа:\n\n{message.json["photo"][0]["file_id"]}\n\n'
                                      f'Проверки ради сообщением ниже я скину эту же картинку, проверь что все ок:')
        bot.send_photo(message.chat.id, message.json["photo"][0]["file_id"])
        send_message(dayofdaypics_chat, f'Юзер {message.chat.id} (@{message.from_user.username}) из группы {group} '
                                 f'добавил картинку дня дня: '
                                 f'\nfile_id:{message.json["photo"][0]["file_id"]}')
        bot.send_photo(dayofdaypics_chat, message.json["photo"][0]["file_id"])

        try:
            with sqlite3.connect(f'{path}admindb/databases/day_of_day.db') as con:
                cur = con.cursor()
                cur.execute("INSERT INTO photos_telegram(link) VALUES (?)", [message.json["photo"][0]["file_id"]])
                cur.execute('SELECT * FROM photos_telegram')
                photos = cur.fetchall()
            send_message(admin_chat, f'База с картинками дня дня успешно обновлена. Всего картиночек теперь: '
                                     f'{len(photos)}')
        except Exception as e:
            send_message(admin_chat, f'База с картинками дня дня не обновлена. Ошибка: '
                                     f'{str(e)}\n{traceback.format_exc()}')
    else:
        send_message(message.chat.id, f'Ошибка: ожидался файл, а мне пришло: {message.content_type}')
        send_message(dayofdaypics_chat, f'Юзер {message.chat.id} пытался скинуть фотку, а скинул сотку: '
                                        f'{message.content_type}\nПодробнее можно глянуть в огурчиках: '
                                        f'{message.date}_{message.chat.id}_{message.id}.pickle')


@bot.message_handler(commands=['add_donator'], is_admin=True)
def add_donator(message):
    dump_message(message)
    print(message)

    msg = send_message(message.chat.id, 'Напиши номер группы, которую нужно добавить в донатеры')
    bot.register_next_step_handler(msg, add_donator_next_step)


def add_donator_next_step(message):
    group_to_add = message.text
    if group_to_add.isdecimal() and len(group_to_add) == 4:

        try:  # Добавление группы
            admin_msg, group_msg, group_chat = add_donator_group(group_to_add, source='tg')
        except Exception as e:
            send_message(admin_chat, f"Ошибка добавления группы-донатера {group_to_add}: {e}")
            return 0

        # Оповещение группы и админов
        notif_status = False
        notif_e = ''
        if group_chat:
            try:
                send_message(group_chat, group_msg)
            except Exception as notif_e:
                pass
            notif_status = True

        admin_msg += f"Сообщение группе {group_to_add}: {'' if not notif_status else 'не '}отправлено"
        admin_msg += f':\n{notif_e}' if notif_e else ''
        send_message(admin_chat, admin_msg)
    return 0


# Команды во всех беседах:
@bot.message_handler(commands=['help'], chat_types=['group', 'supergroup'], is_registered=True)
def help_group(message):
    dump_message(message)

    if message.chat.id == admin_chat:
        send_message(message.chat.id, f'Список доступных команд:'
                                      f'\n/info@kiberded_leti_bot: информация о группе'
                                      f'\n/sms@kiberded_leti_bot - пердеж смс-ок'
                                      f'\n/donaters@kiberded_leti_bot - список донатеров'
                                      f'\n/deds@kiberded_leti_bot - список запущенных сервисов на серваке')
    else:
        send_message(message.chat.id, f'Список доступных команд:'
                                      f'\n/info@kiberded_leti_bot: информация о группе')


# Команды только в админских беседах:
@bot.message_handler(commands=['perni', 'перни', 'sms', 'сообщение'], chat_id=[admin_chat])
def perni(message):
    dump_message(message)

    send_message(message.chat.id, 'Будет добавлено позднее')


@bot.message_handler(commands=['deds', 'деды'], chat_id=[admin_chat])
def deds(message):
    dump_message(message)

    deds_status = subprocess.Popen(["ded", "status", "--without-color"],
                                   stdout=subprocess.PIPE).stdout.read().decode('utf-8')
    send_message(message.chat.id, deds_status)


@bot.message_handler(commands=['donaters', 'донатеры'], chat_id=[admin_chat])
def donaters(message):
    dump_message(message)
    send_message(message.chat.id, get_donators())


# Обработка текстовых сообщений в лс
@bot.message_handler(chat_types='private', is_registered=True)
# обязательно после всех команд и инлайнов! иначе сначала будет обрабатываться эта функция
def text_query(message):
    dump_message(message)

    group = get_group(message.chat.id)
    additional_group = get_additional_group(message.chat.id)
    today = datetime.now(pytz.timezone('Europe/Moscow')).date()

    kb = ''
    kb_message = 'Я тебя не понял.' \
                 '\nНапиши /main для открытия стартовой клавиатуры'  # на всякий случай

    # Выбор клавиатуры и сообщения
    if message.text == 'Расписание 🗓':
        if additional_group and group_study_status(group):
            kb = f'kb_table_{group_study_status(group)}_additional'
        else:
            kb = f'kb_table_{group_study_status(group)}'
        kb_message = f'Сегодня у нас: {get_day()}'  # get_day() по умолчанию today

    elif message.text == 'Календарь 📆':
        kb = 'kb_calendar'
        kb_message = f'Что нам готовит день грядущий? \nСегодня {today} - {get_day()}'

    elif message.text == 'Литература 📚':
        kb = f'{group}_books'
        kb_message = 'Выбирай предмет'

    elif message.text == 'Преподы 👨🏼‍🏫':
        kb = f'{group}_prepods'
        kb_message = 'Выбирай предмет'

    elif message.text == 'Прочее ⚙':
        kb = 'kb_other'
        kb_message = 'Тут будут всякие штуки и шутки'

    elif message.text == 'Полезные ссылки 🔗':
        kb_message = 'Тут находятся всякие полезные ссылки, общие для всей группы. Отредактировать может модератор.'
        kb = f'{group}_links'

    # Отправка клавиатуры и сообщения
    if kb != '':
        markup = open_keyboard(kb)
        send_message(message.chat.id, kb_message, reply_markup=markup)
    else:
        send_message(message.chat.id, kb_message)


# Обработка callback-запросов (inline keyboard)
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    dump_callback(call)
    try:
        payload = callback_to_json(call.data)
    except KeyError:
        group = get_group(call.from_user.id)
        markup = open_keyboard(f'{group}_main')
        kb_message = f'Ошибка навигации - скорее всего, старая клавиатура. Открой новую с главной страницы:'
        send_message(call.from_user.id, text=kb_message, reply_markup=markup)
        return 0
    # bot.answer_callback_query(call.id, 'Будет доступно позже', show_alert=True)
    if payload['type'] == 'navigation':
        group = get_group(call.from_user.id)
        additional_group = get_additional_group(call.from_user.id)

        if "place" not in payload:
            markup = open_keyboard(f'{group}_main')
            kb_message = f'Ошибка навигации - скорее всего, старая клавиатура. Открой новую с главной страницы:'
            send_message(call.from_user.id, text=kb_message, reply_markup=markup)
            return 0

        # endpoint-ы навигации
        endpoint = payload["place"]

        if endpoint == 'table_other':
            kb = f'kb_table_other_{"even" if get_day().split()[1] == "(чёт)" else "odd"}'
            kb_message = f'Если что, сегодня {get_day()}'

        elif endpoint == 'table_other_2':
            kb = f'kb_table_other_{"even" if get_day().split()[1] == "(чёт)" else "odd"}_2'
            kb_message = f'Расписание группы {additional_group}\nЕсли что, сегодня {get_day()}'

        elif endpoint == 'table_prepods':
            kb = f'kb_search_department'
            kb_message = 'Выбери действие'

        elif endpoint == 'settings':
            kb = 'kb_other'
            kb_message = 'Пока что настроек нет. Номер группы можно изменить через /change_group'

        elif endpoint == 'other':  # Назад в Прочее, костыль навигации
            kb = 'kb_other'
            kb_message = f'Тут будут всякие штуки и шутки'

        elif endpoint == 'table_settings':  # Назад в настройки рассылки, костыль навигации
            kb = 'kb_table_settings'
            kb_message = get_tables_settings(call.from_user.id)

        elif endpoint == 'donate':
            donate_status = group_is_donator(group)
            if donate_status:
                # kb = 'kb_settings_donator' todo
                kb = 'kb_other'
                kb_message = f'Спасибо за поддержку проекта! Здесь можно будет управлять функциями, ' \
                             f'доступными группам-донатерам. Нажимай на кнопки, чтобы ' \
                             f'включить/выключить фичу.' \
                             '\nЗадонатить можно переводом на карту сбербанка: ' \
                             '\n4274 3200 7296 2973'
            else:
                kb = 'kb_other'
                kb_message = 'Бот живет и развивается исключительно за счет сообщества' \
                             ' вокруг него.' \
                             '\nЗадонатить можно переводом на карту сбербанка: ' \
                             '\n4274 3200 7296 2973'

        else:
            kb = f'{group}_main'
            kb_message = 'Ошибка навигации. \nДед на связи'
            logger.error(f'Ошибка навигации, вызвана пэйлоадом: {payload["place"]};\n'
                         f'Весь пэйлоад: {payload}')
        if kb != '':
            markup = open_keyboard(kb)
        else:
            markup = ''
        cl = bot.edit_message_text(chat_id=call.from_user.id, text=kb_message, message_id=call.message.id,
                              reply_markup=markup)
        dump_message(cl, callback=True)

    if payload['type'] == 'action':

        group = get_group(call.from_user.id)
        additional_group = get_additional_group(call.from_user.id)
        command = payload["command"]
        next_step = ''  # вместо шизы, так сказать

        if command == 'table_today':
            if additional_group:
                kb = f'kb_table_{group_study_status(group)}_additional'
            else:
                kb = f'kb_table_{group_study_status(group)}'
            message_ans = read_table(group)

        elif command == 'table_tomorrow':
            if additional_group:
                kb = f'kb_table_{group_study_status(group)}_additional'
            else:
                kb = f'kb_table_{group_study_status(group)}'
            message_ans = read_table(group, get_day(today + timedelta(days=1)))

        elif command == 'table_weekday':
            kb = f'kb_table_other_{"even" if get_day().split()[1] == "(чёт)" else "odd"}'
            message_ans = read_table(group, payload["weekday"])

        elif command == 'table_exam':
            if additional_group:
                kb = f'kb_table_{group_study_status(group)}_additional'
            else:
                kb = f'kb_table_{group_study_status(group)}'
            message_ans = get_exams(group)

        elif command == 'table_today_2':
            if additional_group:
                kb = f'kb_table_{group_study_status(group)}_additional'
            else:
                kb = f'kb_table_{group_study_status(group)}'
            message_ans = f'Расписание группы {additional_group}\n' + read_table(additional_group)

        elif command == 'table_tomorrow_2':
            if additional_group:
                kb = f'kb_table_{group_study_status(group)}_additional'
            else:
                kb = f'kb_table_{group_study_status(group)}'
            message_ans = f'Расписание группы {additional_group}\n' + \
                          read_table(additional_group, get_day(today + timedelta(days=1)))

        elif command == 'table_weekday_2':
            kb = f'kb_table_other_{"even" if get_day().split()[1] == "(чёт)" else "odd"}_2'
            message_ans = f'Расписание группы {additional_group}\n' + \
                          read_table(additional_group, payload["weekday"])

        elif command == 'table_exam_2':
            if additional_group:
                kb = f'kb_table_{group_study_status(group)}_additional'
            else:
                kb = f'kb_table_{group_study_status(group)}'
            message_ans = f'Расписание группы {additional_group}\n' + get_exams(additional_group)

        elif command == 'table_empty':  # todo открывать расписание пораньше?
            kb = f'kb_table_{group_study_status(group)}'
            message_ans = 'Расписание на новый семестр еще не выложено, ' \
                          'следи за апдейтами на digital.etu.ru/schedule ' \
                          '\nРасписание в боте появляется на следующий день после выхода'

        elif command == 'table_back':
            if additional_group:
                kb = f'kb_table_{group_study_status(group)}_additional'
            else:
                kb = f'kb_table_{group_study_status(group)}'
            message_ans = f'Сегодня у нас: {get_day()}'  # get_day() по умолчанию today

        elif command == 'get_books':
            kb = ''
            message_ans = ''
            try:
                normal_subject = get_subject_from_id(payload["subject"], group)
                get_books(normal_subject, group, call)
            except Exception as e:
                message_ans = 'Произошла ошибка. Админы уже знают, скоро починят'  # todo а знают ли?
                send_message(admin_chat, f'Ошибка в get_books: {e}\nГруппа {group}\n\n'
                                         f'Traceback:\n{traceback.format_exc()}')

        elif command == 'get_prepods':
            kb = f'{group}_prepods'
            try:
                normal_subject = get_subject_from_id(payload["subject"], group)
                message_ans = get_prepods(normal_subject, group)
            except Exception as e:
                message_ans = 'Произошла ошибка. Админы уже знают, скоро починят'
                send_message(admin_chat, f'Ошибка в get_prepods: {e}\nГруппа {group}'
                                         f'\n\nTraceback:\n{traceback.format_exc()}')

        elif command == 'calendar_today':
            if call.from_user.id in list_unauthorized_users:
                message_ans = f'Ошибка доступа - календарь группы могут смотреть только авторизованные участники. ' \
                             f'Чтобы получить доступ, зарегистрируйся в сообществе ВКонтакте: https://vk.com/kiberded_bot' \
                             f' \nВ случае возникновения сложностей можешь писать админам: ' \
                             f'https://t.me/evgeniy_setrov или https://t.me/TSheyd'
                kb = ''
            else:
                kb = 'kb_calendar'
                message_ans = read_calendar(group)  # по умолчанию read_calendar('today')

        elif command == 'calendar_tomorrow':
            if call.from_user.id in list_unauthorized_users:
                message_ans = f'Ошибка доступа - календарь группы могут смотреть только авторизованные участники. ' \
                             f'Чтобы получить доступ, зарегистрируйся в сообществе ВКонтакте: https://vk.com/kiberded_bot' \
                             f' \nВ случае возникновения сложностей можешь писать админам: ' \
                             f'https://t.me/evgeniy_setrov или https://t.me/TSheyd'
                kb = ''
            else:
                kb = 'kb_calendar'
                message_ans = read_calendar(group, 'tomorrow')

        # закомментированное - это то, что отсутствует в create_keyboards, так что надо смотреть аккуратнее

        # elif command == 'remove_notifications':
        # pass

        elif command == 'random_anecdote':
            kb = 'kb_other'
            message_ans = get_random_anekdot()

        elif command == 'random_toast':
            kb = 'kb_other'
            message_ans = get_random_toast()

        elif command == 'anecdote_subscribe':
            kb = 'kb_other'
            message_ans = add_user_to_anekdot(call.from_user.id, '1', source='tg')

        elif command == 'anecdote_unsubscribe':
            kb = 'kb_other'
            message_ans = add_user_to_anekdot(call.from_user.id, '-1', source='tg')

        elif command == 'table_subscribe':
            kb = 'kb_table_settings'
            message_ans = add_user_to_table(call.from_user.id, '1', source='tg')

        elif command == 'table_unsubscribe':
            kb = 'kb_other'
            message_ans = add_user_to_table(call.from_user.id, '-1', source='tg')

        elif command == 'set_tables_mode':
            kb = 'kb_set_tables_mode_cal' if groups[group]['calendar'] else 'kb_set_tables_mode'
            message_ans = f'Доступные режимы рассылки расписания:' \
                          f'\n{"Календарь - расписание из календаря" if groups[group]["calendar"] else ""}' \
                          f'\nЕжедневное - каждый день расписание на завтра (если завтра есть пары)' \
                          f'\nЕженедельное - каждое воскресенье на всю следующую неделю' \
                          f'\nОба - собственно, оба варианта.'

        elif command == 't_mode_set':
            mode = payload['mode']
            kb = 'kb_table_settings'
            message_ans = set_table_mode(call.from_user.id, mode)

        elif command == 'set_tables_time':
            kb = ''
            message_ans = 'Напиши время отправки сообщения в формате ЧЧ:ММ'
            next_step = set_tables_time

        elif command == 'change_group':
            kb = ''
            message_ans = 'Введи номер группы в формате ХХХХ, например 9281'
            next_step = change_group_step

        elif command == 'change_additional_group':
            kb = ''
            message_ans = 'Введи номер дополнительной группы в формате ХХХХ, например 9281\n\n' \
                          'Чтобы удалить доп.группу, напиши 0000'
            next_step = change_additional_group_step

        elif command == 'search_department':
            list_id = payload['list_id']
            kb = f'kb_departments_{list_id}'
            message_ans = f'Выбери кафедру преподавателя:'

        elif command == 'search_prepod':
            list_id = payload['list_id']
            department_id = payload['department_id']
            kb = f'kb_prepods_{department_id}_{list_id}'
            message_ans = f'Выбери преподавателя:'

        elif command == 'choose_department':
            department_id = payload['id']
            kb = f'kb_prepods_{department_id}_0'
            message_ans = f'Выбери преподавателя:'

        elif command == 'choose_prepod':  # TODO copy to quotes
            prepod_id = payload['id']
            kb = f'SPECIAL;choose_prepod;{prepod_id}'
            prepod, department = get_prepod_info(prepod_id)
            message_ans = f'Расписание преподавателя: {prepod[2]} {department}\nСегодня у нас: {get_day()}'
            add_prepod_to_history(prepod_id, call.from_user.id)

        elif command == 'prepods_history':
            kb = ''
            message_ans = ''
            try:
                get_prepods_history(call)
            except Exception as e:
                message_ans = 'Произошла ошибка. Админы уже знают, скоро починят'
                send_message(admin_chat, f'Ошибка в get_prepods: {e}\nГруппа {group}'
                                         f'\n\nTraceback:\n{traceback.format_exc()}')

        elif command == 'search_prepod_text':
            kb = ''
            message_ans = 'Напиши фамилию преподавателя. Поиск НЕ чувствителен к регистру и может исправлять ' \
                          'опечатки'
            next_step = search_prepod_text_step

        elif command == 'table_prepod':
            prepod_id = payload['id']
            kb = f'SPECIAL;choose_prepod;{prepod_id}'
            weekday = payload['weekday']
            message_ans = get_prepod_schedule(prepod_id, weekday)

        elif command == 'minigames':
            kb = 'kb_minigames'
            message_ans = 'Выбери мини-игру:'

        elif command == 'heads_or_tails_toss':
            kb = 'kb_heads_or_tails_retoss'
            message_ans = get_coin_flip_result(call.from_user.id)

        elif command == 'start_classical_RPC':
            kb = 'SPECIAL;start_classical_RPC'
            markup = start_classical_rock_paper_scissors(call.from_user.id, int(time.time()))
            message_ans = 'Игра началась!'

        elif command == 'classical_RPC':
            kb = 'kb_minigames'
            id = payload['id']
            choose = payload['choose']
            if choose == 'c':  # отмена типа
                message_ans = stop_classical_rock_paper_scissors(call.from_user.id, id)
            else:
                message_ans = classical_rock_paper_scissors(call.from_user.id, id, choose)

        elif command == 'cancel_set_lk_secrets':
            bot.clear_step_handler_by_chat_id(chat_id=call.from_user.id)
            kb = ''
            message_ans = 'Ввод данных отменен'

        elif command == 'attendance_checkin':
            kb = ''
            message_ans = ''  # для того, чтобы просто вызвать функцию отмечания

            check_in_at_lesson(call.from_user.id, payload["id"])


        # elif command == 'add_chat':
        # pass

        # elif command == 'day_of_day_toggle':
        # pass

        # elif command == 'weekly_toast_toggle':
        # pass

        else:  # все остальное - типа обработка ошибков
            kb = ''
            message_ans = 'Ошибка - неизвестная команда'  # дефолтное значение
            logger.error(f'Ошибка ответа на запрос {command};'
                         f'\nПэйлоад: {payload}')

        if message_ans:  # get_books возвращает 0, так что вот
            if kb:
                if kb.startswith('SPECIAL'):  # обработка специальных случаев
                    kb = kb.split(';')
                    if kb[1] == 'choose_prepod':
                        markup = kb_prepod_schedule(kb[2], get_day())
                    elif kb[1] == 'start_classical_RPC':
                        markup = markup  # тут все норм
                    else:
                        markup = ''
                else:
                    markup = open_keyboard(kb)
            else:
                markup = ''
            if next_step:
                msg = send_message(call.from_user.id, message_ans, reply_markup=markup)
                bot.register_next_step_handler(msg, next_step)
            else:
                cl = bot.edit_message_text(chat_id=call.from_user.id, text=message_ans, message_id=call.message.id,
                                      reply_markup=markup)
                dump_message(cl, callback=True)


# обработка inline-запросов
@bot.inline_handler(lambda query: (len(query.query) == 4) and query.query.isdecimal())
def query_text(inline_query):
    text = inline_query.query
    if not check_group_exists(text):
        r = types.InlineQueryResultArticle('1', f'Группы {text} не найдено', types.InputTextMessageContent(f'Группы {text} не найдено'))
        bot.answer_inline_query(inline_query.id, [r])
    else:
        r = types.InlineQueryResultArticle('1', 'Расписание на сегодня', types.InputTextMessageContent(
            f'Группа {text}. {read_table(text)}'))
        r2 = types.InlineQueryResultArticle('2', 'Расписание на завтра', types.InputTextMessageContent(
            f'Группа {text}. {read_table(text, get_day(today + timedelta(days=1)))}'))
        r3 = types.InlineQueryResultArticle('3', 'Расписание на все дни', types.InputTextMessageContent(
            f'{read_table(text, "full (нечёт)")}\n\n{read_table(text, "full (чёт)")}'))
        bot.answer_inline_query(inline_query.id, [r, r2, r3])


# Обработка миграций в супергруппу
@bot.message_handler(content_types='migrate_to_chat_id')
def migration(message):
    dump_message(message)

    from_id = message.chat.id
    to_id = message.migrate_to_chat_id

    try:
        with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
            cur = con.cursor()
            group = cur.execute("SELECT group_id FROM group_gcals WHERE tg_chat_id=?", [from_id]).fetchone()[0]
            if group:
                cur.execute("UPDATE group_gcals SET tg_chat_id=? WHERE group_id=?", (to_id, group))
                send_message(admin_chat, f'Произошла миграция группы: {from_id} -> {to_id}. Данные в базе обновлены, '
                                         f' группа {group}')
            else:
                send_message(admin_chat, f'Произошла миграция группы: {from_id} -> {to_id}. Данные в базе НЕ обновлены:'
                                         f' не было найдено такой беседы в group_gcals')
        send_message(to_id, 'Тип группы изменился на супергруппу (скорее всего кто-то поменял настройки админов), '
                            'id беседы был изменен.')
    except Exception as e:
        send_message(admin_chat, f'Произошла миграция группы: {from_id} -> {to_id}. При обновлении базы произошла'
                                 f' ошибка: {str(e)}, traceback:\n{traceback.format_exc()}')


bot.add_custom_filter(custom_filters.ChatFilter())  # необходимо для фильтра chat_id админских команд
bot.add_custom_filter(IsRegistered())  # фильтр регистрации юзера
bot.add_custom_filter(IsModerator())  # фильтр на модератора
bot.add_custom_filter(IsAdmin())  # фильтр на админа

create_backup_dir()  # создание папки для бэкапов
update_list_registered_users()  # обновление переменной list_registered_users
update_moderators()  # обновление переменной moderators
update_admins()  # обновление переменной admins
update_prepods()
update_groups_data()


def main(after_crash=False, log=True):
    try:
        text_addition = '' if not after_crash else ' после ошибки.'  # сообщение об ошибке может быть и не доставлено
        if log:
            send_message(admin_chat, f'Кибертележный дед активирован{text_addition}')
        logging.warning(f'Кибертележный дед активирован{text_addition}')

        bot.polling(non_stop=True)
    except ReadTimeout:
        log = False
    except ConnectionError:
        log = False
    except Exception as e:
        send_message(admin_chat, f'Произошла ошибка тележного: {str(e)}\n{traceback.format_exc()}')
        logging.critical(f'Произошла ошибка тележного: {str(e)}\n{traceback.format_exc()}')
        log = True
    finally:
        main(after_crash=True, log=log)  # не в except, т.к. send_message тоже может вызвать exception


if __name__ == "__main__":
    main()

bot.send_document()
