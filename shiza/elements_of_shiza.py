#! /usr/bin/env python
# -*- coding: utf-8 -*-
# dependencies: [chat_bot]

"""
В этом файле находятся функции, которые должны выполняться в отдельных потоках (отдельные потоки - шиза)
"""

import logging
import requests
import toml
import sys
import sqlite3
import traceback
import subprocess
from datetime import date, timedelta
import json
import vk_api
import os
import time
import math
from vk_api.utils import get_random_id
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from shiza.databases_shiza_helper import watch_all_databases, edit_all_databases, edit_database, \
    get_group, generate_subject_keyboards, edit_admin_database, add_moderator, create_database, get_database_to_watch, \
    change_user_group, get_common_group, edit_email, edit_gcal, add_preset_books, view_email, view_gcal, delete_email, \
    delete_gcal, get_stock_groups, change_user_additional_group, get_common_additional_group, check_group_exists, \
    load_table_cache, load_calendar_cache, add_donator_group

# common init
logger = logging.getLogger('chat_bot')
try:
    config = toml.load('configuration.toml')
except FileNotFoundError:
    logger.critical('configuration.toml не найден!')
    sys.exit()

path_db = config.get('Kiberded').get('path')
group_id = config.get('Kiberded').get('group_token')
token = config.get('Kiberded').get('token')
# \common init

days = [['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'], [' (чёт)', ' (нечёт)']]
lesson_numbers_allowed = ['1', '2', '3', '4', '5', '6', '7', '8']
parity_allowed = ['0', '1']

global vk_session
global vk


def initialization():
    global vk
    global vk_session

    vk_session = vk_api.VkApi(token=token)
    vk = vk_session.get_api()
    logger.warning('Запуск Шизы')
    return 0


def open_keyboard(keyboard) -> str:
    """
    Чтение клавиатуры из JSON в path/keyboards

    :param str keyboard: название клавиатуры
    :return str: клавиатура
    """

    with open(f'{path_db}keyboards/{keyboard}.json', 'r', encoding='utf-8') as f:
        result = f.read()
    return result


def send_message(peer_id=2000000001, message='Ошибка - пустое сообщение', attachment='', keyboard='') -> None:
    """
    Отправка сообщения с обработкой Flood-control

    :param int peer_id: id для отправки сообщения. По умолчанию - отладочная беседа, но для читаемости лучше прописывать
    :param str message: сообщение, обязательный аргумент
    :param attachment: вложение (опционально)
    :param str keyboard: клавиатура (из open_keyboard())
    """

    try:
        vk.messages.send(
            peer_id=peer_id,
            random_id=get_random_id(),
            message=message,
            attachment=attachment,
            keyboard=keyboard)
    except vk_api.exceptions.ApiError as vk_error:
        if '[9]' in str(vk_error):  # ошибка flood-control: если флудим, то ждем секунду ответа
            logger.warning('Flood-control, спим секунду')
            time.sleep(1)
            send_message(peer_id, message, attachment, keyboard)
        elif '[914]' in str(vk_error):  # message is too long
            for i in range(math.floor(len(message)/4096)):
                send_message(peer_id, message[i*4096:i*4096+4096], attachment, keyboard)
            if len(message)%4096 != 0:
                send_message(peer_id, message[-(len(message)%4096):], attachment, keyboard)
            elif attachment:
                send_message(peer_id, message, attachment, keyboard)
        else:
            raise Exception(str(vk_error))


def shiza_main(user_id, freedom, isAdmin):  # работа с базами данных через вк
    """
    Основной скрипт Шизы, здесь осуществляется управление редактором БД в чат-боте. 
    Редакторов два - один для модераторов групп, в котором можно редактировать БД своей группы (****.db), 
    другой админский - для редактирования общих баз и ручного запуска парсинга БД всех групп.

    :param int user_id: id пользователя (после @id)
    :param str freedom: уровень доступа к редактору - 'user'/'moderator'/'admin'
    :param bool isAdmin: if True and freedom=='admin', работа с админским редактором баз.
        Иначе переключает.
    :return: 0
    """

    initialization()
    group = str(get_group(path=path_db, user_id=user_id)[0])

    # Настройки path для админского редактора при IsAdmin
    if isAdmin:
        path = f'{path_db}admindb/'
    else:  # Если не isAdmin, то и для админского доступа модераторский редактор (собственной группы)
        path = path_db
        if freedom == 'admin':
            freedom = 'moderator'

    logger.warning(f'Запущена шиза databases юзером @id{str(user_id)} из группы {group}')
    longpoll = VkBotLongPoll(vk_session, group_id)
    send_message(peer_id=user_id,
                 message=f'Редактор БД запущен. Права доступа: {freedom}',
                 keyboard=open_keyboard(f'kb_shiza_{freedom}'))

    for event in longpoll.listen():
        logger.warning(f'Новый event в шизе databases: {str(event.type)}')
        if event.type == VkBotEventType.MESSAGE_NEW and event.obj.message["peer_id"] == user_id:
            try:
                payload = json.loads(event.obj.message["payload"])
                
                # Важно! payload["type"] для Шизы должен отличаться от того, что в основном боте.
                # Иначе будет некорректный ответ на кнопки

                if payload["type"] == "shiza_navigation":  # Навигация по клавиатурам
                    shiza_endpoint = payload["place"]
                    if shiza_endpoint == "end_databases":  # Выход
                        send_message(peer_id=user_id, message='Дед на связи.')
                        return 0

                    elif shiza_endpoint == "start_databases":  # Запуск
                        kb = f'kb_shiza_{freedom}'
                        kb_message = 'Редактор БД. Что требуется?'

                    elif shiza_endpoint == 'view_email':
                        kb = 'kb_email'
                        kb_message = f'{view_email(group)}\n.\n' \
                                     f'Бот умеет присылать оповещения о письмах на почте в беседу группы, для этого необходимо: ' \
                                     f'\n1) Добавить бота в беседу группы. Помимо оповещений, он еще будет ежедневно ' \
                                     f'присылать расписание на день и закреплять его (для закрепления нужно дать ему ' \
                                     f'права администратора. Для этого функционала необязательно добавлять почту/календарь)' \
                                     f'\n2) В настройках почтового ящика необходимо включить IMAP. Это стандартная ' \
                                     f'настройка, используемая для разных почтовых сервисов типа outlook. ' \
                                     f'Также нужно создать там же отдельный пароль для приложения' \
                                     f'\n3) Когда сделаешь все вышеперечисленное, нажми на "Внести данные".\n' \
                                     f'Подробнее про добавление почты написано в статье ' \
                                     f'"Кибердед: инструкция по применению" на странице сообщества.'

                    elif shiza_endpoint == 'view_calendar':
                        kb = 'kb_gcal'
                        kb_message = f'{view_gcal(group)}\n.\n' \
                                     f'Бот умеет присылать мероприятия из iCalendar-календаря ' \
                                     f'(Google-календарь, Яндекс-календарь и проч.), в который можно ' \
                                     f'добавлять ссылки на зум и все такое - это, зачастую, очень удобно.' \
                                     f' Тогда бот будет ежедневно присылать в беседу его вместо обычного ' \
                                     f'расписания, а в ЛС с ботом появится вкладка "Календарь". ' \
                                     f'Чтобы добавить календарь, нужно скопировать в настройках календаря' \
                                     f' "Интеграция календаря - закрытый адрес в формате iCal" и ' \
                                     f'отправить его боту. Для отправки, нажми на "Внести данные".\n' \
                                     f'Подробнее про добавление календаря написано в статье ' \
                                     f'"Кибердед: инструкция по применению" на странице сообщества.'

                    elif shiza_endpoint == "add_preset_books_info":
                        kb = 'kb_books'
                        kb_message = 'Здесь ты можешь выбрать для своей группы методички по умолчанию - ' \
                                     'это список файлов, созданный кем-то под твою группу (а может еще не' \
                                     ' созданный, тогда раздел с методичками будет пустой).\n' \
                                     'Ранее внесенные изменения в этот раздел сбросятся, так что если ' \
                                     'были какие-то изменения, лучше сделать бэкап (через "просмотр БД")' \
                                     '\nДля добавления методичек по своему усмотрению см. статью ' \
                                     'на странице сообщества.'

                    else:  # обработка всех остальных пэйлоадов
                        kb = f'kb_shiza_{freedom}'
                        kb_message = 'Ошибка редактора - неизвестная клавиатура'
                        logger.error(f'Ошибка навигации шизы - {payload["place"]}\n'
                                     f'Весь пэйлоад: {payload}')

                    send_message(peer_id=user_id, keyboard=open_keyboard(kb), message=kb_message)

                elif payload["type"] == "shiza_action":
                    shiza_command = payload["command"]

                    if shiza_command == "watch_databases":
                        message_ans, kb = watch_all_databases(path=path, group=group, freedom=freedom)
                        send_message(peer_id=user_id, keyboard=kb, message=message_ans)

                    elif shiza_command == "edit_databases":
                        message_ans, kb = edit_all_databases(path=path, group=group, freedom=freedom)
                        send_message(peer_id=user_id, keyboard=kb, message=message_ans)

                    elif shiza_command == "read_database":
                        if group == payload["database"] or freedom == 'admin':
                            get_database_to_watch(payload["database"], path)
                            send_message(peer_id=user_id, message=f'Создаем файл {payload["database"]}.xlsx...')
                            upload = vk_api.VkUpload(vk_session)
                            file = upload.document_message(f'{path}cache/{payload["database"]}.xlsx',
                                                           peer_id=user_id,
                                                           title=f'{payload["database"]}')
                            send_message(peer_id=user_id, message='а вот и он:',
                                         attachment=f'doc{user_id}_{file.get("doc").get("id")}')
                            os.remove(f'{path}cache/{payload["database"]}.xlsx')
                            send_message(peer_id=user_id, message='Не забудь выключить редактор БД.',
                                         keyboard=open_keyboard('kb_end'))
                        else:
                            send_message(peer_id=user_id,
                                         keyboard=open_keyboard(f'kb_shiza_{freedom}'),
                                         message='Ошибка доступа')

                    elif shiza_command == "edit_database":  # todo лень было переделывать, но тут некрасиво

                        if freedom != 'admin' and payload["database"] != group:
                            send_message(peer_id=user_id, message='Эта база тебе недоступна, браток.')

                        elif isAdmin:  # админская шиза
                            send_message(peer_id=user_id, message='Меняй БД на базе имеющихся файлов',
                                         keyboard=open_keyboard('kb_end'))

                            for event in longpoll.listen():  # Получение присланного файла из диалога
                                if event.type == VkBotEventType.MESSAGE_NEW and \
                                        event.obj.message["peer_id"] == user_id:

                                    if event.obj.message["attachments"]:
                                        attachments = event.obj.message["attachments"][0]
                                        attachment = attachments.get("doc")
                                        url = attachment.get("url")

                                        send_message(peer_id=user_id, message=f'Загрузка базы по ссылке: {url}')
                                        send_message(peer_id=2000000001,
                                                     message=f'@id{user_id} меняет админскую базу '
                                                             f'{payload["database"]}')

                                        try:  # если криво загрузилось и не получилось отредактировать
                                            edit_admin_database(database=payload["database"], path=path,
                                                                url=url)
                                            send_message(peer_id=user_id, message=f'Готово!',
                                                         keyboard=open_keyboard(f'kb_shiza_{freedom}'))
                                        except ValueError as e:
                                            send_message(peer_id=user_id,
                                                         message=f'Ошибка в базе данных: {e}\n'
                                                                 f'Исправь файл и попробуй еще раз')
                                        except Exception as e:
                                            os.remove(f"{path}cache/{payload['database']}.xlsx")
                                            os.remove(f"{path}cache/{payload['database']}.db")
                                            send_message(peer_id=user_id,
                                                         message=f'Ошибка редактора - недопустимый формат',
                                                         keyboard=open_keyboard(f'kb_shiza_{freedom}'))
                                            send_message(peer_id=2000000001,
                                                         message=f'@id{user_id} ломает админскую базу '
                                                                 f'{payload["database"]}\n{e}')
                                            logger.error(f'Ошибка редактирования админской БД: '
                                                         f'{e}\n{traceback.format_exc()}')

                                    elif event.obj.message['payload']:
                                        send_message(peer_id=user_id, message=f'Редактор БД. Что требуется?',
                                                     keyboard=open_keyboard(f'kb_shiza_{freedom}'))
                                    break

                        else:  # обычная шиза
                            get_database_to_watch(database=payload["database"], path=path)
                            send_message(peer_id=user_id, message='Экспортируем имеющуюся БД...')
                            upload = vk_api.VkUpload(vk_session)
                            file = upload.document_message(f'{path}cache/{payload["database"]}.xlsx',
                                                           peer_id=user_id,
                                                           title=f'{payload["database"]}')

                            send_message(peer_id=user_id, message='Вот файл-образец:',
                                         attachment=f'doc{user_id}_{file.get("doc").get("id")}')
                            os.remove(f'{path}cache/{payload["database"]}.xlsx')
                            send_message(peer_id=user_id, message='Загрузи новый .xslx файл, оформленный '
                                                                  'строго по шаблону',
                                         keyboard=open_keyboard('kb_end'))

                            for event in longpoll.listen():  # Получение присланного файла из диалога
                                if event.type == VkBotEventType.MESSAGE_NEW and \
                                        event.obj.message["peer_id"] == user_id:
                                    if event.obj.message["attachments"]:
                                        attachments = event.obj.message["attachments"][0]
                                        attachment = attachments.get("doc")
                                        url = attachment.get("url")

                                        send_message(peer_id=user_id, message=f'Загрузка базы по ссылке: {url}')
                                        send_message(peer_id=2000000001,
                                                     message=f'@id{user_id} меняет базу {payload["database"]}')

                                        try:
                                            edit_database(database=payload["database"], path=path, url=url,
                                                          group=group)
                                            send_message(peer_id=user_id, message=f'Готово!',
                                                         keyboard=open_keyboard(f'kb_shiza_{freedom}'))
                                        except ValueError as e:
                                            send_message(peer_id=user_id,
                                                         message=f'Ошибка в базе данных: {e}\n'
                                                                 f'Исправь файл и попробуй еще раз')

                                        except Exception as e:
                                            os.remove(f"{path}cache/{payload['database']}.xlsx")
                                            os.remove(f"{path}cache/{payload['database']}.db")
                                            send_message(peer_id=user_id, message=f'Ошибка редактора - '
                                                                                  f'недопустимый формат',
                                                         keyboard=open_keyboard(f'kb_shiza_{freedom}'))
                                            send_message(peer_id=2000000001, message=f'@id{user_id} ломает базу'
                                                                                     f' {payload["database"]}\n{e}')
                                            logger.error(f'Ошибка редактирования БД: '
                                                         f'{e}\n{traceback.format_exc()}')

                                    elif event.obj.message['payload']:
                                        send_message(peer_id=user_id, message=f'Редактор БД. Что требуется?',
                                                     keyboard=open_keyboard(f'kb_shiza_{freedom}'))
                                    break

                    elif shiza_command == 'reset_database':
                        send_message(peer_id=user_id,
                                     message=f'Сбрасываем {group}.db к значениям по умолчанию')
                        send_message(peer_id=2000000001,
                                     message=f'Ивент в шизе: @id{user_id} сбрасывает БД {group}')
                        refresh_db_status, admin_book_str = create_database(group)
                        send_message(peer_id=user_id,
                                     message=refresh_db_status)
                        send_message(peer_id=2000000001,
                                     message=admin_book_str)

                    elif shiza_command == 'parse_all_databases':  # Обновление БД всех групп (расписание/преподы/методички)
                        if freedom == 'admin':
                            send_message(peer_id=user_id,
                                         message=f'Запущен парсинг БД... \nЭто займет некоторое время')
                            all_groups = get_stock_groups()
                            send_message(peer_id=2000000001,
                                         message=f'АХТУНГ! Запущен парсинг БД. Обновляем {len(all_groups)} БД')
                            parsing_message = ''

                            for group in all_groups:
                                try:
                                    parser_msg_user, parser_msg_admin = create_database(group,
                                                                                        is_global_parsing=True)
                                except Exception as err:
                                    send_message(peer_id=2000000001, message=f'Ошибка парсинга БД {group}: {err}')
                                    continue

                                parsing_message += parser_msg_admin

                            load_table_cache()
                            load_calendar_cache()

                            send_message(peer_id=2000000001, message=parsing_message)
                            send_message(peer_id=user_id, message=f'Готово!',
                                         keyboard=open_keyboard(f'kb_shiza_{freedom}'))

                        else:
                            send_message(peer_id=user_id, message=f'Ошибка доступа',
                                         keyboard=open_keyboard(f'kb_shiza_{freedom}'))

                    elif shiza_command == "add_moderator":

                        # В зависимости от уровня доступа, можно назначить модератора в любую группу или в свою
                        if freedom != 'admin':
                            send_message(peer_id=user_id, keyboard=open_keyboard('kb_end'),
                                         message=f'Ты можешь дать кому-нибудь из своей группы права на редактирование '
                                                 f'расписания, напиши кого добавить в формате user_id(без @id)'
                                                 f'например (@id) {user_id} (это ты). Id можно посмотреть в адресной '
                                                 f'строке браузера')

                        elif freedom == 'admin':
                            send_message(peer_id=user_id, keyboard=open_keyboard('kb_end'),
                                         message=f'Напиши кого добавить в формате user_id/group, '
                                                 f'например {user_id}/{group} (это ты)')

                        # Получение сообщения
                        for event in longpoll.listen():
                            if event.type == VkBotEventType.MESSAGE_NEW and \
                                    event.obj.message["peer_id"] == user_id:
                                # разбиваем сообщение для проверки данных
                                values_check = str(event.obj.message['text']).split('/')

                                # добавление от админа
                                if len(values_check) == 2 and values_check[0].isdecimal() and \
                                        values_check[1].isdecimal() and freedom == 'admin':
                                    add_mod_response = add_moderator(values_check[0], values_check[1])
                                    send_message(peer_id=user_id, message=add_mod_response,
                                                 keyboard=open_keyboard('kb_end'))
                                    if add_mod_response == f'Пользователь @id{values_check[0]} добавлен в модераторы':
                                        send_message(peer_id=2000000001,
                                                     message=f'@id{user_id} добавил модератора '
                                                             f'группы {values_check[1]}: '
                                                             f'{add_mod_response.split()[1]}')

                                        if f'{group}.db' not in os.listdir(f'{path_db}databases/'):
                                            send_message(peer_id=user_id,
                                                         message=f'Создаем БД {values_check[1]}..')
                                            add_db_response, admin_add_db_response = create_database(
                                                values_check[1])  # Создаем БД только если модера и БД не было
                                            send_message(peer_id=2000000001, message=admin_add_db_response)
                                            send_message(peer_id=user_id, message=add_db_response)

                                        books_message, admin_books_message = add_preset_books(values_check[1])
                                        generate_subject_keyboards(group)  # генерируем клавиатуры предметов

                                        notification = f'Тебя сделали модератором группы {values_check[1]}, ' \
                                                       f'теперь ты можешь добавить в бота почту и гугл-' \
                                                       f'календарь, а также редактировать базу данных группы.' \
                                                       f'\n{books_message}'
                                        try:
                                            send_message(peer_id=values_check[0], message=notification)
                                        except Exception as e:  # если нет пользователя, которого назначили
                                            if '[901]' in str(e):
                                                send_message(peer_id=user_id,
                                                             message='Сообщение новому модератору не '
                                                                     'отправлено - отсутствует получатель')
                                        send_message(peer_id=2000000001, message=admin_books_message)

                                # добавление от модератора
                                elif len(values_check) == 1 and values_check[0].isdecimal():
                                    # проверяем что поц из той же группы
                                    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
                                        cur = con.cursor()
                                        id_check = cur.execute(
                                            "SELECT group_id FROM user_ids WHERE user_id=? AND group_id=?",
                                            (values_check[0], group)).fetchone()
                                    if id_check:
                                        add_mod_response = add_moderator(values_check[0], group)
                                        notification = f'Тебя сделали модератором группы {values_check[1]}, ' \
                                                       f'теперь ты можешь добавить в бота чат группы и почту,' \
                                                       f' а также редактировать базу данных группы.'
                                        try:
                                            send_message(peer_id=values_check[0], message=notification)
                                        except Exception as e:
                                            # если в боте нет указанного пользователя, он будет добавлен, но сообщение до него не дойдет
                                            if '[901]' in str(e):
                                                send_message(peer_id=user_id,
                                                             message='Сообщение новому модератору не '
                                                                     'отправлено - отсутствует получатель')

                                        send_message(peer_id=user_id, message=add_mod_response,
                                                     keyboard=open_keyboard('kb_end'))
                                        send_message(peer_id=2000000001,
                                                     message=f'В группе {group} @id{user_id} добавил модератора'
                                                             f' {add_mod_response.split()[1]}')
                                    else:
                                        send_message(peer_id=user_id, message=f'Ошибка - @id{values_check[0]} '
                                                                              f'не состоит в группе {group}.',
                                                     keyboard=open_keyboard('kb_end'))
                                        break

                                # Важно! Это всегда в конце, иначе будет всплывать KeyError из-за payload
                                elif event.obj.message['payload']:
                                    send_message(peer_id=user_id, message=f'Редактор БД. Что требуется?',
                                                 keyboard=open_keyboard(f'kb_shiza_{freedom}'))
                                break

                    # Добавление группы в донатеры
                    elif shiza_command == "add_donator":
                        if freedom == 'admin':
                            send_message(peer_id=user_id, keyboard=open_keyboard('kb_end'),
                                         message=f'Напиши группу, из которой пришел донат:')

                            for event in longpoll.listen():
                                if event.type == VkBotEventType.MESSAGE_NEW and \
                                        event.obj.message["peer_id"] == user_id:

                                    group_to_add = str(event.obj.message['text'])
                                    if group_to_add.isdecimal() and len(group_to_add) == 4:

                                        admin_msg, group_msg, group_chat = add_donator_group(group_to_add, source='vk')

                                        # Ответ админу
                                        send_message(peer_id=user_id,
                                                     message=admin_msg,
                                                     keyboard=open_keyboard(f'kb_shiza_{freedom}'))

                                        # Оповещение группы
                                        notif_success = False
                                        if group_chat:
                                            try:
                                                send_message(peer_id=group_chat,
                                                             message=group_msg)
                                                notif_success = True
                                            except vk_api.ApiError:  # не отправить в конфу, ну и ладно
                                                pass
                                            except TypeError:  # нет конфы, ну и ладно
                                                pass

                                        # Оповещение админского чатика ВК
                                        send_message(peer_id=2000000001,
                                                     message=f'{admin_msg}\n'
                                                             f'Уведомление в конфу {group_chat}: '
                                                             f'{"" if notif_success else "не"} отправлено')

                                    # Важно! Это всегда в конце, иначе будет всплывать KeyError из-за payload
                                    elif event.obj.message['payload']:
                                        send_message(peer_id=user_id, message=f'Редактор БД. Что требуется?',
                                                     keyboard=open_keyboard(f'kb_shiza_{freedom}'))
                                    break

                    elif shiza_command == 'edit_email':  # добавление почты
                        send_message(peer_id=user_id, keyboard=open_keyboard('kb_end'),
                                     message='Напиши почту/пароль без пробелов через "/" в формате '
                                             '\nmailaddress@email.ru/password\nПроверяй правильность данных!')

                        for event in longpoll.listen():
                            if event.type == VkBotEventType.MESSAGE_NEW and \
                                    event.obj.message["peer_id"] == user_id:

                                data_to_add = str(event.obj.message["text"]).strip(' /').split('/')
                                if len(data_to_add[0].split('@')) == 2 and len(data_to_add) == 2:

                                    edit_email(group, data_to_add[0], data_to_add[1])
                                    subprocess.Popen(["systemctl", "restart", "mail_bot"], stdout=subprocess.PIPE)
                                    send_message(peer_id=user_id,
                                                 message=f'Почта {data_to_add[0]} добавлена. Теперь бот будет '
                                                         f'присылать в беседу группы (если она есть) оповещения'
                                                         f' о новых письмах.\nРекомендуем проверить '
                                                         f'работоспособность, отправив что-нибудь на ту почту.'
                                                         f'\n.\n{view_email(group)}')
                                    send_message(peer_id=2000000001,
                                                 message=f'Ивент в шизе: @id{user_id} добавляет почту {group}')
                            # Важно! Это всегда в конце, иначе будет всплывать KeyError из-за payload
                            elif event.obj.message['payload']:
                                send_message(peer_id=user_id, message=f'Редактор БД. Что требуется?',
                                             keyboard=open_keyboard(f'kb_shiza_{freedom}'))
                            break

                    elif shiza_command == 'edit_calendar':  # добавление календаря
                        send_message(peer_id=user_id, keyboard=open_keyboard('kb_end'),
                                     message='Напиши ссылку на календарь:')
                        for event in longpoll.listen():
                            if event.type == VkBotEventType.MESSAGE_NEW and \
                                    event.obj.message["peer_id"] == user_id:
                                data_to_add = str(event.obj.message["text"])
                                try:  # простая проверка на качество ссылки
                                    print(requests.get(data_to_add).text)
                                    edit_gcal(group, data_to_add)
                                    send_message(peer_id=user_id,
                                                 message=f'Календарь {data_to_add} добавлен. '
                                                         f'Можешь проверить работоспособность'
                                                         f' во вкладке "Календарь".\n.\n{view_gcal(group)}')
                                    send_message(peer_id=2000000001, message=f'Ивент в шизе: @id{user_id} '
                                                                             f'добавляет календарь {group}')
                                except Exception as e:
                                    send_message(peer_id=2000000001, message=f'Ивент в шизе: @id{user_id} не '
                                                                             f'может добавить календарь {group}'
                                                                             f'\n{e}{traceback.format_exc()}')
                                    raise ValueError('нерабочая ссылка. Проверь правильность и попробуй еще раз')

                            # Важно! Это всегда в конце, иначе будет всплывать KeyError из-за payload
                            elif event.obj.message['payload']:
                                send_message(peer_id=user_id, message=f'Редактор БД. Что требуется?',
                                             keyboard=open_keyboard(f'kb_shiza_{freedom}'))
                            break

                    elif shiza_command == 'delete_email':  # удаление почты
                        send_message(peer_id=user_id, message=f'Удаляем следующие данные:\n{view_email(group)}')
                        delete_email(group)
                        send_message(peer_id=user_id, message='Готово!',
                                     keyboard=open_keyboard(f'kb_shiza_{freedom}'))
                        send_message(peer_id=2000000001,
                                     message=f'Ивент в шизе: @id{user_id} из {group} удаляет почту')
                        subprocess.Popen(["systemctl", "restart", "mail_bot"], stdout=subprocess.PIPE)

                    elif shiza_command == 'delete_calendar':  # удаление календаря
                        send_message(peer_id=user_id, message=f'Удаляем следующие данные:\n{view_gcal(group)}')
                        delete_gcal(group)
                        send_message(peer_id=user_id, message='Готово!',
                                     keyboard=open_keyboard(f'kb_shiza_{freedom}'))
                        send_message(peer_id=2000000001,
                                     message=f'Ивент в шизе: @id{user_id} из {group} удаляет календарь')
                    elif shiza_command == 'view_email':
                        send_message(peer_id=user_id, message=view_email(group))

                    elif shiza_command == 'view_calendar':
                        send_message(peer_id=user_id, message=view_gcal(group))

                    elif shiza_command == "add_preset_books":
                        message_moder, message_admin = add_preset_books(group)
                        generate_subject_keyboards(group)  # генерируем клавиатуры предметов и преподов
                        send_message(peer_id=user_id, message=message_moder,
                                     keyboard=open_keyboard(f'kb_shiza_{freedom}'))
                        send_message(peer_id=2000000001, message=f'Ивент в шизе: {message_admin}')

                    else:
                        message_ans = 'Ошибка редактора - неизвестная команда'
                        kb = f'kb_shiza_{freedom}'
                        logger.error(f'Ошибка шизы - неизвестная команда: {payload["command"]}')
                        send_message(peer_id=user_id, keyboard=kb, message=message_ans)

                # выход из шизы при нажатии кнопок клавиатуры
                elif payload["type"] in ['action', 'navigation']:  # команды из основного бота
                    send_message(peer_id=user_id, keyboard=open_keyboard(f'kb_other'),
                                 message='Работа редактора прекращена')
                    return 0

            # Обработка ошибок

            except KeyError:  # Обработка криво введенных текстовых данных
                send_message(peer_id=user_id, keyboard=open_keyboard(f'kb_shiza_{freedom}'),
                             message=f'Ошибка - проверь правильность введенных данных. '
                                     f'Взаимодействуй с ботом кнопками на клавиатуре')

            except ValueError as e:  # Еще обработка кривых текстовых данных
                send_message(peer_id=user_id, keyboard=open_keyboard(f'kb_shiza_{freedom}'),
                             message=f'Ошибка - {e}. '
                                     f'Взаимодействуй с ботом кнопками на клавиатуре')

            except Exception as e:  # Все остальные ошибки
                error_message = f'Ошибка - неизвестная команда. Работа редактора прекращена.\n' \
                                f'Используй кнопки на клавиатуре, чтобы взаимодействовать с ботом'
                if e != 'payload':
                    logger.error(f'Ошибка шизы: {e}\n{traceback.format_exc()}')
                    if freedom == 'admin':
                        error_message += f'\n{e}\n{traceback.format_exc()}'
                send_message(peer_id=user_id, keyboard=open_keyboard(f'kb_other'), message=error_message)
                return 0


def change_group_func(user_id):
    """
    Мини-Шиза для настройки номера группы обычным пользователем
    Данный поток должен быть недоступен пользователям с freedoom = 'admin' / 'moderator'

    :param int user_id: id пользователя
    :return:
    """

    initialization()

    group = get_common_group(path=path_db, user_id=user_id)
    logger.warning(f'Запущена шиза change_user юзером @id{str(user_id)} из группы {group}')
    longpoll = VkBotLongPoll(vk_session, group_id)
    send_message(peer_id=user_id, message=f'Напиши номер своей группы')

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW and event.obj.message["peer_id"] == user_id:

            values_check = str(event.obj.message['text']).strip()
            if len(values_check) == 4 and values_check.isdecimal():  # проверка формата данных на всякий
                send_message(peer_id=user_id, message='Секунду, ищем группу...')

                # проверка на существование группы
                with sqlite3.connect(f'{path_db}admindb/databases/group_ids.db') as con:
                    cur = con.cursor()
                    group_data = cur.execute('SELECT etu_id, studying_type FROM group_gcals WHERE group_id=?',
                                             [values_check]).fetchone()

                if group_data:

                    if group_data[1] == 'заоч':  # todo поддержка групп заочников
                        send_message(peer_id=user_id,
                                     message='Извини, поддержки групп заочников не завезли - не думали мы что этот бот '
                                             'так далеко зайдет. Если интересно воспользоваться ботом, напиши админам и'
                                             ' мы допилим его для вас ;)')
                        return 0

                    if not check_group_exists(values_check):
                        send_message(peer_id=user_id,
                                     message=f'Ошибка - группа {values_check} не найдена. '
                                             f'Проверь правильность номера или обратись к администраторам')
                        return 0

                    group_exists, user_existed, answer_cg = change_user_group(values_check, user_id)

                    # Оповещения о смене номера группы
                    if group_exists:
                        if user_existed:
                            change_group_notif = f'@id{user_id} сменил(-а) группу с {group} на {values_check}'
                        else:
                            change_group_notif = f'@id{user_id} присоединился к группе {values_check}'
                        send_message(peer_id=2000000001, message=change_group_notif)
                    else:
                        send_message(peer_id=2000000001,
                                     message=f'@id{user_id} пришел к нам из дикой {values_check}. '
                                             f'Неплохо бы назначить им модератора')
                        # Создаем БД если модератора не было, на всякий случай
                        add_db_response, admin_add_db_response = create_database(values_check)
                        send_message(peer_id=2000000001, message=admin_add_db_response)
                        send_message(peer_id=user_id, message=add_db_response)
                    send_message(peer_id=user_id, message=answer_cg, keyboard=open_keyboard(f'{values_check}_main'))
                else:
                    send_message(peer_id=user_id, keyboard=open_keyboard('kb_change_group'),  # TODO remove
                                 message=f'Ошибка. Группа {values_check} не найдена. '
                                         f'Проверь правильность номера или обратись к администраторам')
            else:
                send_message(peer_id=user_id,
                             message='Ошибка. Проверь правильность введенного номера. '
                                     'Нажми на "Изменить группу" еще раз.')
            return 0


def change_additional_group_func(user_id):  # смена/установка номера группы юзером
    """
    Мини-Шиза для настройки дополнительного номера группы пользователем

    :param int user_id: id пользователя
    :return: message для беседы, в которую добавили бота
    """

    initialization()

    user_group = str(get_group(path=path_db, user_id=user_id)[0])
    group = get_common_additional_group(path=path_db, user_id=user_id)
    logger.warning(f'Запущена шиза change_additional_group юзером @id{str(user_id)} из группы {group}')
    longpoll = VkBotLongPoll(vk_session, group_id)
    send_message(peer_id=user_id, message=f'Напиши четырехзначный номер группы. Чтобы убрать доп.группу из вкладки '
                                          f'"Расписание", просто выйди из настроек')
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW and event.obj.message["peer_id"] == user_id:
            values_check = str(event.obj.message['text']).strip()
            if len(values_check) == 4 and values_check.isdecimal():  # проверка формата
                send_message(peer_id=user_id, message='Секунду, ищем группу...')
                # проверка на существование такой группы
                with sqlite3.connect(f'{path_db}admindb/databases/group_ids.db') as con:
                    cur = con.cursor()
                    group_data = cur.execute('SELECT etu_id, studying_type FROM group_gcals WHERE group_id=?',
                                             [values_check]).fetchone()
                if group_data:
                    if group_data[1] == 'заоч':
                        send_message(peer_id=user_id,
                                     message='Извини, поддержки групп заочников не завезли - не думали мы что этот бот '
                                             'так далеко зайдет. Если интересно воспользоваться ботом, напиши админам и'
                                             ' мы допилим его для вас ;)')
                        return 0

                    if not check_group_exists(values_check):
                        send_message(peer_id=user_id,
                                     message=f'Ошибка - группа {values_check} не найдена. '
                                             f'Проверь правильность номера или обратись к администраторам')
                        return 0

                    user_existed, answer_cg = change_user_additional_group(values_check, user_id)
                    # это можно потом поменять если будет флуд, пока по приколу пусть будет
                    change_group_notif = f'@id{user_id} сменил(-а) доп.группу с {group} на {values_check}'
                    send_message(peer_id=2000000001, message=change_group_notif)


                    send_message(peer_id=user_id, message=answer_cg,
                                 keyboard=open_keyboard(f'{user_group}_main'))
                else:
                    send_message(peer_id=user_id,
                                 message=f'Ошибка. Группа {values_check} не найдена. '
                                         f'Проверь правильность номера или обратись к администраторам. \n'
                                         f'Изменения не внесены.')
            else:
                values_check = None
                user_existed, answer_cg = change_user_additional_group(values_check, user_id)
                send_message(peer_id=user_id,
                             message='Дополнительная группа удалена. Если не хотел ее убирать - '
                                     'проверь правильность введенного номера')
                change_group_notif = f'@id{user_id} сменил(-а) доп.группу с {group} на {values_check}'
                send_message(peer_id=2000000001, message=change_group_notif)
            return 0


def add_chat(group, chat_id, freedom):  # добавление чата в group_ids
    """
    Мини-Шиза для добавления беседы группы с кнопки на странице сообщества

    :param str group: номер группы
    :param int chat_id: chat_id
    :param str freedom: уровень доступа пользователя (если 'user', то chat_id не может быть переназначен)
    :return: message для беседы, в которую добавили бота
    """

    with sqlite3.connect(f'{path_db}admindb/databases/group_ids.db') as con:
        cur = con.cursor()

        old_chat_id, tg_chat_id = cur.execute('SELECT vk_chat_id, tg_chat_id '
                                              'FROM group_gcals '
                                              'WHERE group_id=?', [group]).fetchone()
        if old_chat_id:  # если уже была куда-то добавлена эта группа
            if freedom == 'user' and old_chat_id[0] != chat_id:
                return f'Ошибка - недостаточно прав. Беседа этой группы уже была подключена кем-то ' \
                       f'(chat_id={old_chat_id}), переназначить чат группы может только модератор группы. ' \
                       f'Обратись к кому-нибудь из администраторов.'

        cur.execute("UPDATE group_gcals SET vk_chat_id=? WHERE group_id=?", (chat_id, group))
        gr_inf = cur.execute("SELECT group_id FROM group_gcals WHERE vk_chat_id=?", [chat_id]).fetchone()[0]

    if tg_chat_id is not None:
        tg_msg = f' Обнаружена беседа группы в Телеграме. Синхронизация бесед пока недоступна - в ТГ не будут ' \
                 f'присылаться уведомления с почты и проч., только расписание\nМожно создать новую беседу в ТГ и ' \
                 f'добавить туда Кибердеда - команда [club201485931|@kiberded_bot] телеграм'
        # tg_msg = f'Обнаружена беседа группы в Телеграме. Чтобы привязать ее к этой беседе (либо создать новую ' \
        #          f'и отвязать ту), используйте команду \n[club201485931|@kiberded_bot] телеграм'
    else:
        tg_msg = f' Также Кибердед есть в Telegram! Зайти можно во вкладке "Прочее" в чат-боте. ' \
                 f'Добавить беседу группы можно по команде: \n[club201485931|@kiberded_bot] телеграм'

    chat_message = f'Группа {gr_inf} успешно добавлена.\n' \
                   f'Бот будет ежедневно присылать расписание на день, а также может присылать ' \
                   f'уведомления о новых письмах на почте группы (если подключить почту). Расписание ' \
                   f'создается на основе расписания на сайте ЛЭТИ и может изменяться модератором ' \
                   f'группы. Также вместо расписания бот может присылать ивенты на день с ' \
                   f'гугл-календаря (при наличии).' \
                   f'\nОстальной функционал доступен в ЛС с ботом' \
                   f'\nСписок возможных команд в чате:\n' \
                   f'[club201485931|@kiberded_bot] инфо' \
                   f'\n.\n{tg_msg}'

    return chat_message


def set_tables_time_vk(user_id):
    """
    Настройка подписки на расписания (время рассылки)
    """
    initialization()

    logger.warning(f'Запущена шиза set_tables_time юзером @id{str(user_id)}')
    longpoll = VkBotLongPoll(vk_session, group_id)
    send_message(peer_id=user_id, message='Напиши время отправки сообщения в формате ЧЧ:ММ')

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW and event.obj.message["peer_id"] == user_id:
            time_ = str(event.obj.message['text'])

            if len(time_) != 5:  # Дополняем нулями, если необходимо
                time_ = time_.zfill(5)

            try:  # Проверка формата времени
                time_check = time.strptime(time_, '%H:%M')
            except ValueError:
                msg = 'Ошибка - проверь формат сообщения (ЧЧ:ММ), нажми кнопку и попробуй еще раз'
                send_message(peer_id=user_id, message=msg)
                return False

            with sqlite3.connect(f'{path_db}admindb/databases/table_ids.db') as con:
                cur = con.cursor()
                upd_query = f'UPDATE `vk_users` SET time=? WHERE id=?'
                cur.execute(upd_query, (time_, user_id))
                con.commit()

            msg = f'Время рассылки расписания установлено: {time_}. Изменения вступят в силу со следующего дня'
            send_message(peer_id=user_id, message=msg)
            return True


def empty_thread():  # пустой поток на случай ошибки в пэйлоаде или где-то еще
    return 0
