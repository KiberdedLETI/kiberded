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
from fun.anekdot import get_random_toast
from bot_functions.bots_common_funcs import get_last_lesson, read_calendar, read_table, get_day, set_table_mode, \
    get_exam_notification
from bot_functions import attendance as attendance
from shiza.etu_parsing import update_groups_params, load_calendar_cache, load_table_cache, \
    parse_prepods_schedule, load_prepods_table_cache, parse_exams, parse_prepods_db
from shiza.databases_shiza_helper import generate_prepods_keyboards, generate_departments_keyboards, \
    remove_old_data, create_database
import sys
import pickle
import pandas as pd
global config
global vk_session
global vk
global num_of_anekdots
import os

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
num_of_anekdots = config.get('Kiberded').get('num_of_base')  # количество анекдотов в базе
timetable = config.get('Kiberded').get('timetable')
path = config.get('Kiberded').get('path')
cron_time = config.get('Kiberded').get('cron_time')
tables_time = config.get('Kiberded').get('tables_time')
is_sendCron = config.get('Kiberded').get('is_sendCron')
is_sendToast = config.get('Kiberded').get('is_sendToast')
tg_admin_chat = config.get('Kiberded').get('telegram_admin_chat')
# /common init

bot = telebot.TeleBot(tg_token)
now_date = datetime.now().strftime('%Y-%m-%d')  # необходимо для бэкапов сообщений

folder = f'{path}messages_backup/{now_date}'
if not os.path.isdir(f'{folder}'):
    os.mkdir(f'{folder}')

def send_vk_message(message, peer_id, attachment=''):
    """
    Отправка сообщения с обработкой Flood-control

    :param int peer_id: id беседы или пользователя для отправки сообщения.
    :param str message: сообщение, обязательный аргумент
    :param str attachment: вложение (опционально)
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
            send_vk_message(message, peer_id)
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
                send_vk_message(message[i * 4096:i * 4096 + 4096], peer_id)
            if len(message) % 4096 != 0:  # последний кусок сообщения
                send_vk_message(message[-(len(message) % 4096):], peer_id, attachment)
            elif attachment:  # если вдруг длина сообщения кратна 4кб и есть вложение - отправляем его без текста
                send_vk_message(message='', peer_id=peer_id, attachment=attachment)
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
    with open(f'{path}messages_backup/{date}/schedule_{date_mes}_{chat_id}_{message_id}.pickle', 'ab') as f:
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
        query = f'UPDATE user_ids SET tg_last_msg={message.message_id} WHERE tg_id={message.chat.id}'
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


def pin_vk_message(response, peer_id):  # закрепление сообщения (если есть права администратора беседы)
    try:
        message_id = response[0].get('conversation_message_id')
        if message_id:
            vk_session.method('messages.pin', {"peer_id": peer_id, "conversation_message_id": message_id, "v": 5.131})
        else:
            error = response[0].get('error')
            if error['code'] == 7:
                pass  # Кикнули из беседы или нет прав
            else:
                send_vk_message(f'Что-то сломалось с закрепом сообщения у chat_id={peer_id}'
                                f'\nmessage_id={message_id}\nmessage:\n{response}', 2000000001)

    except vk_api.exceptions.ApiError as vk_error:
        if '[9]' in str(vk_error):  # ошибка flood-control: если флудим, то ждем секунду ответа
            time.sleep(1)
            pin_vk_message(message_id, peer_id)
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

    :param int num: номер анекдота (0 - num_of_anekdots)
    :return: анекдот.
    """

    with sqlite3.connect(f'{path}anekdots.db') as db:
        cursor = db.cursor()
        cursor.execute('SELECT text FROM anekdots WHERE id=?', [num])
        data = cursor.fetchall()
        text = data[0][0]
    if text == 'ERROR':  # Пахнет рекурсией
        get_anekdot(random.randint(0, num_of_anekdots))
    anekdot_str = text[3:-4]
    return anekdot_str


def get_day_photo() -> str:
    """
    Получение рандомной ссылки на фотографию для донатного ежедневного сообщения расписания в беседу (пока только ВК)
    :return: ссылка на фотографию
    """

    with sqlite3.connect(f'{path}admindb/databases/day_of_day.db') as con:
        cursor = con.cursor()
        cursor.execute('SELECT count_field FROM count')
        data = cursor.fetchone()
        numphotos = int(data[0])
        cursor.execute('SELECT link FROM photos')
        all_photos = cursor.fetchall()
        photo = all_photos[random.randint(0, numphotos-1)][0]
    con.close()
    return photo


def get_groups() -> pd.DataFrame:
    """
    Получение списка групп, ссылок на календарь и chat_ids
    :return: df[[group_id, gcal_link, vk_chat_id, tg_chat_id, tg_last_msg, send_tables]] (index=group_id)
    """
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        q = ("SELECT group_id, gcal_link, vk_chat_id, tg_chat_id, tg_last_msg, send_tables, "
             "gcal_over_tables, gcal_over_exams, is_donator, with_dayofday FROM group_gcals")
        df = pd.read_sql(q, con).set_index('group_id')
    return df


def update_study_status(group):
    """
    Ежедневная проверка состояния группы (is_Study, is_Exam) с сопутствующим запуском разных функций парсинга данных

    :param group: группа
    :return: is_exam, is_study (bool 0/1), сообщение с оповещением об изменении
    """

    # также парсит периодически расписание на предмет обновлений.
    today = date.today()
    daily_return_str = ''
    session_str = ''  # Возможно здесь по умолчанию можно сделать сообщение об ошибке

    # достаем из БД параметры "идет ли семестр" и "идет ли сессия"
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        all_dates = cur.execute(f'SELECT semester_start, semester_end, exam_start, exam_end, isStudy, isExam '
                                f'FROM group_gcals WHERE group_id=?', [group]).fetchall()[0]

    # переводим в дату, чтобы можно было сравнить
    semester_start = datetime.strptime(all_dates[0], '%Y-%m-%d').date()
    semester_end = datetime.strptime(all_dates[1], '%Y-%m-%d').date()
    is_study_old = all_dates[4]
    is_exam_old = all_dates[5]

    # обновляем bool isStudy и isExam
    is_study = 1 if semester_start <= today <= semester_end else 0

    try:  # isExam внутри try, потому что не у всех групп есть сессия (exam_start, exam_end)
        exam_start = datetime.strptime(all_dates[2], '%Y-%m-%d').date()
        exam_end = datetime.strptime(all_dates[3], '%Y-%m-%d').date()
        is_exam = 1 if exam_start <= today <= exam_end else 0  # обновляем данные

        # если семестр скоро закончится, пробуем подтянуть данные сессии
        if today+timedelta(days=14) >= semester_end and today <= exam_start:
            session_str, is_exam = parse_exams(group)

    except TypeError:  # нет exam_start/end
        is_exam = 0

    # записываем новые is_study и is_exam
    with con:
        cur.execute("UPDATE group_gcals SET isStudy=?, isExam=? WHERE group_id=?", [is_study, is_exam, group])
    con.close()

    # В период сессии обновляем расписание сессии, еженедельно
    if today.weekday() == 2 and is_exam:
        daily_return_str += parse_exams(group)

    # пытаемся (чуть-чуть) заранее подгружать расписание до начала семестра/сессии todo
    #if semester_start-timedelta(days=2) <= today:  # осенью эт получается 30-08, зимой ~ начало февраля, норм
        #parse_group_params(group)  # пытаемся заранее подгружать даты нового сема

    # дальше реакции на 4 варианта изменения параметров - началась сессия/конец сессии, начался сем/конец сема*
    if is_exam != is_exam_old:
        # Начались экзамены
        if is_exam:
            # session str получено при обновлении is_exam
            daily_return_str = f'Началась сессия! Выживут не все, но будет весело.\n{session_str}\n' \
                               f'Расписание экзаменов всегда можно посмотреть во вкладке "Расписание" ' \
                               f'чат-бота.\n\nУдачи!\n'

        # Кончились экзамены
        else:
            parse_exams(group, set_default_next_sem=True)  # удаляем расписание экзаменов
            daily_return_str = f'С окончанием сессии! До встречи в следующем семестре. ' \
                               f'А пока, Дед переходит в спящий режим.'

    if is_study != is_study_old:  # todo не работает в личке
        # Начался семестр
        if is_study:
            # стираем старые БД; генерируем новое.
            refresh_db_status, admin_book_str = create_database(group)
            daily_return_str = f'С началом семестра! Теперь Дед будет ежедневно присылать утром расписание' \
                               f' на день.\nРасписание, список предметов и преподавателей, а также всякие' \
                               f' методички всегда можно посмотреть в чат-боте.\nУспехов!\n{refresh_db_status}\n' \
                               f'P.S. Методички предыдущего семестра, при наличии, должны быть доступны ближайший ' \
                               f'месяц, специально для любителей допсы.'
        # Кончился семестр
        else:
            daily_return_str = 'С окончанием семестра! Дед переходит в спящий режим, расписания больше не будут ' \
                               'присылаться. \nУдачи!'

    if is_study and today-timedelta(days=28) >= semester_start:  # если кончилась допса
        data_removed = remove_old_data(group)
        if data_removed:
            daily_return_str = f'Из базы данных удалены методички предыдущего семестра.\nКто не закрылся - F.'

    if daily_return_str:
        daily_return_str += f'\n'  # форматирование итогового сообщения
    return is_exam, is_study, daily_return_str



def cron():
    """
    Большая функция, в которой отправляются расписания и прочие штуки по беседам групп,
    а также обновляются данные БД каждой группы.

    :return:
    """

    # В первые и последние месяцы семестров пару раз в неделю обновляем etu_ids и даты семестра/сессии
    if date.today().strftime('%m') in ['01', '02', '05', '06', '08', '09', '12'] and date.today().weekday() in [0, 4]:
        try:
            send_tg_message(tg_admin_chat, "Парсинг etu_id's. Проверь корректность данных!!!:\n")
            admin_message, deleted_groups, deleted_users = update_groups_params()
            send_tg_message(tg_admin_chat, admin_message)

            # Рассылка оповещений об удалении группы - по чатам групп и по пользователям
            if not deleted_groups.empty:
                for row in deleted_groups.itertuples():
                    msg = (f"Группа {row.group_id} была удалена из базы данных - "
                           f"вероятно, из-за слияния групп или завершения обучения."
                           f"\nДанные беседы группы и пользователей (включая модераторов) удалены из бота."
                           f"\nЧтобы повторно подключить беседу группы, удалите и добавьте бота заново, "
                           f"предварительно выбрав в ЛС новый номер группы.")


                    if row.vk_chat_id:
                        try:
                            send_vk_message(msg, row.vk_chat_id)
                        except Exception as e:
                            pass
                    if row.tg_chat_id:
                        try:
                            send_tg_message(row.tg_chat_id, msg)
                        except Exception as e:
                            pass

            if not deleted_users.empty:
                for row in deleted_users.itertuples():
                    msg = f"Твоя группа {row.group_id} была удалена из базы данных - " \
                          f"вероятно, из-за слияния групп или завершения обучения." \
                          f"\nЕсли считаешь, что произошла ошибка, напиши админам: " \
                          f"https://t.me/evgeniy_setrov или https://t.me/TSheyd"

                    if row.tg_id:
                        try:
                            send_tg_message(row.tg_id, f"{msg}\nЧтобы выбрать другую группу, напиши /change_group")
                        except Exception as e:
                            pass
                    if row.vk_id:
                        try:
                            send_vk_message(f"{msg}\nЧтобы выбрать другую группу, напиши что-нибудь.", row.vk_id)
                        except Exception as e:
                            pass

        except KeyError as e:
            send_tg_message(tg_admin_chat, e)
        except Exception as e:
            err_message = f'Ошибка парсинга etu_id: {e}\n{traceback.format_exc()}'
            send_tg_message(tg_admin_chat, err_message)
            logger.critical(f"{err_message}")

    # Раз в месяц обновляем расписание преподавателей
    if date.today().day == 3:
        try:
            parse_prepods_db()  # Парсинг списка преподавателей и списка кафедр
            parse_prepods_schedule()  # Парсинг расписания преподавателей
            load_prepods_table_cache()  # Загрузка кэша
            generate_departments_keyboards()  # Генерация клавиатур с обновленным списком кафедр
            generate_prepods_keyboards()
        except Exception as prepods_parsing_err:
            send_tg_message(tg_admin_chat, f"Ошибка обновления расписания преподавателей: {prepods_parsing_err}")

    # структура сообщения: донатное (добавляется последним) + update_study_status() + расписание/календарь (при наличии)

    load_calendar_cache()  # На всякий обновляем кэш календаря и расписания перед отправкой
    load_table_cache()

    group_data = get_groups()
    group_data = group_data.loc[~group_data.index.duplicated()]

    # логи для отправки отчета в админский чат
    log_msg = ""
    log_msg_vk = []
    log_msg_tg = []

    send_vk_message('Ежедневный крон', 2000000001)
    send_tg_message(tg_admin_chat, 'Ежедневный крон')

    for group in group_data.index:
        vk_chat = group_data.loc[group, 'vk_chat_id']  # int by default
        tg_chat = group_data.loc[group, 'tg_chat_id']
        msg = ""
        attachment = ""

        try:
            # обновление данных - изменения в учебном состоянии (семестр/сессия)
            is_exam, is_study, daily_str = update_study_status(group)

            # Если отключена отправка расписания в конфу - на этом всё, едем дальше.
            if not group_data.loc[group, 'send_tables']:
                continue

            # Собираем сообщение с расписанием: календарь если прописан календарь (независимо от учебного статуса),
            # иначе обычное расписание если учеба, плюс оповещение об экзаменах/консультациях, если таковые есть.
            gcal_over_tables = bool(group_data.loc[group, 'gcal_over_tables'])
            gcal_over_exams = bool(group_data.loc[group, 'gcal_over_exams'])

            table = read_calendar(group) if gcal_over_tables else read_table(group) if is_study else ""
            if table.split()[-1] not in ['Пусто', '\nПусто']:
                msg += table

            if is_exam and not gcal_over_exams:
                exam_msg = get_exam_notification(group)
                if exam_msg:
                    msg += f"\n{exam_msg}"

            # Проверка на содержательность сообщения
            if not daily_str and not msg:
                continue

            msg = f"{daily_str}\n{msg}"

            # ежедневная пикча для донатеров
            if group_data.loc[group, 'is_donator'] and group_data.loc[group, 'with_dayofday']:
                attachment = get_day_photo()

            # Отправка сообщения в нужный чат
            if vk_chat:
                vk_chat = int(vk_chat)
                response = send_vk_message(message=msg, peer_id=vk_chat, attachment=attachment)
                pin_vk_message(response, vk_chat)
                log_msg_vk += [f"{group} - {'календарь' if gcal_over_tables else 'расписание'}\n"]

            if tg_chat:
                if group_data.loc[group, 'tg_last_msg']:  # Открепляем предыдущее, если оно было
                    unpin_tg_message(tg_chat, group_data.loc[group, 'tg_last_msg'])
                msg_ = send_tg_message(tg_chat, msg)
                pin_tg_message(msg_)
                log_msg_tg += [f"{group} - {'календарь' if gcal_over_tables else 'расписание'}\n"]

        except Exception as send_tables_err:
            log_msg += (f"{group} - ОШИБКА {send_tables_err}"
                        f"\n{traceback.format_exc()}\n"
                        f"--------- vk: {vk_chat}\n"
                        f"--------- tg: {tg_chat}\n"
                        f"--------- attach: {attachment}\n"
                        f"--------- msg: {msg}\n\n")
            continue

    log_msg = f"Выполнена рассылка расписаний\n" \
              f"VK ({len(log_msg_vk)}):\n{''.join(log_msg_vk)}\n\n" \
              f"TG ({len(log_msg_tg)}):\n{''.join(log_msg_tg)}\n\n" \
              f"{log_msg}"

    send_tg_message(tg_admin_chat, log_msg)
    send_vk_message(log_msg, 2000000001)
    return 0


def get_group(user_id, source='vk') -> str:  # принимает user_id и возвращает его группу
    """
    Получение номера группы пользователя

    :param int user_id: id пользователя
    :param source: vk | tg, по умолчанию vk
    :return: номер группы
    """

    id_col = 'vk_id' if source == 'vk' else 'tg_id'

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        cur.execute(f"SELECT group_id FROM user_ids WHERE {id_col}=?", [user_id])
        group = cur.fetchone()

    if group:
        group = group[0]
    else:
        return '0000'
    return group


def get_anekdot_user_ids(source='vk') -> list:  # список юзеров для рассылки анекдотов
    """
    Получение списка пользователей, подписанных на анекдоты.

    :param str source: 'vk' / 'tg' - источник сообщения
    :return: список [(user_id, count), ...]
    """
    with sqlite3.connect(f'{path}admindb/databases/anekdot_ids.db') as con:
        cursor = con.cursor()
        data = []
        cursor.execute(f'CREATE TABLE IF NOT EXISTS {source}_users(id text, count text, source text)')

        for row in cursor.execute(f'SELECT `id`, `count` FROM {source}_users'):
            data.append(tuple((int(row[0]), int(row[1]))))
    con.close()
    return data


def anekdots():
    """
    Отправка анекдотов в цикле всем подписанным
    """
    ids = get_anekdot_user_ids(source='vk')
    for id in ids:
        try:
            msg = "Ежедневные анекдоты:\n" if id[1] > 1 else "Ежедневный анекдот:\n"
            msg += '\n'.join([get_anekdot(random.randint(0, num_of_anekdots)) for k in range(id[1])])
            send_vk_message(msg, id[0])
        except Exception as e:
            send_vk_message(f"Ошибка отправки {id[1]} анекдотов юзеру @{id[0]}: {e}", 2000000001)

    ids = get_anekdot_user_ids(source='tg')
    for id in ids:
        try:
            msg = "Ежедневные анекдоты:\n" if id[1] > 1 else "Ежедневный анекдот:\n"
            msg += '\n'.join([get_anekdot(random.randint(0, num_of_anekdots)) for k in range(id[1])])
            send_tg_message(id[0], msg)
        except Exception as e:
            send_tg_message(tg_admin_chat, f"Ошибка отправки {id[1]} анекдотов юзеру @{id[0]}: {e}")
    return 0


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


def get_user_table_ids(source='vk') -> dict:  # список юзеров для рассылки расписания
    """
    Получение списка пользователей, подписанных на ежедневное расписание, а также параметров рассылки
    :param str source: 'vk' / 'tg' - источник сообщения
    todo refactor in dataframe format
    :return: {"time": {"type":[user_ids], ...}, ...};
        "time"=None - дефолтное время, "type"='None' дефолтный режим рассылки.
    """

    with sqlite3.connect(f'{path}admindb/databases/table_ids.db') as con:
        cursor = con.cursor()
        data = []

        cursor.execute(f'CREATE TABLE IF NOT EXISTS `{source}_users` (id text, count text, type text, time text)')

        query = f'SELECT id, count, type, time FROM `{source}_users`'
        for row in cursor.execute(query):
            data.append(tuple((int(row[0]), tuple((int(row[1]), str(row[2]), str(row[3]))))))
    con.close()

    # Форматируем в {"time": {"type":[user_ids], ...}, ...}
    # Для ВК формат тот же, для совместимости, однако функционала пока нет todo
    result = {}
    for user_id, user_settings in data:
        table_mode = user_settings[1]
        table_time = user_settings[2]

        data = result.setdefault(table_time, {})
        data.setdefault(table_mode, []).append(user_id)

    return result


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
        tg_last_messages = cur.execute('SELECT tg_id, tg_last_msg '
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

                    # состояние группы (семестр/сессия)
                    is_exam, is_study, daily_str = update_study_status(group)

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

                    if table_type == 'calendar':
                        cal_message = read_calendar(group, date='tomorrow')
                        if cal_message:
                            table_message = str(cal_message)
                        else:
                            set_table_mode(user_id, source=source, mode='daily')
                            table_message += '\nПроизошла ошибка рассылки расписания - тип рассылки "Календарь", но ' \
                                             'календарь не найден.\nУстановлен тип рассылки по умолчанию - "Ежедневный"'

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
                                send_vk_message(message, user_id)

                            logger.warning(f'Расписание отправлено юзеру {user_id} из гр. {group}')

                except Exception:
                    error_message = f'Произошла ошибка при отправке расписания: {traceback.format_exc()}\n' \
                                    f'Юзер {user_id}, группа {group}'
                    send_vk_message(error_message, 2000000001)
                    send_tg_message(tg_admin_chat, error_message)


def check_toast():
    """
    Проверка необходимости отправки тоста

    :return: 0
    """

    now_time = datetime.today().strftime('%H:%M')

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        all_groups = cur.execute("SELECT group_id, vk_chat_id, tg_chat_id FROM group_gcals WHERE with_toast=1").fetchall()

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
    send_vk_message(toast_message, chat_id)
    if tg_chat_id:
        send_tg_message(tg_chat_id, toast_message)
    logger.warning(f'Тост отправлен группе с peer_id={chat_id}; в telegram - {tg_chat_id}')
    return 0


def attendance_schedule():
    """
    Рассылка в тг уведомлений об отмечаемости тем, кто подписан на данный сервис.
    :return: 0
    """
    now_time = time.gmtime(time.time())

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        all_users = cur.execute(
            "SELECT tg_id, lk_email, lk_password, failed_login_attempts FROM user_ids WHERE attendance_cron=1").fetchall()

        for i in range(len(all_users)):
            tg_id, email, password, failed_login_attempts = all_users[i][0], all_users[i][1], all_users[i][2], \
                                                            all_users[i][3]

            # загрузка статы за день
            session = attendance.start_new_session()
            code, session = attendance.auth_in_lk(session, email, password)
            if code != 200:
                if failed_login_attempts <= 2:
                    msg = send_tg_message(tg_id, 'Аутентификация в ЛК для работы с посещаемостью не удалась. Возможно, '
                                                 'в базе хранятся неактуальные данные.')
                    cur.execute("""UPDATE user_ids SET failed_login_attempts = ? WHERE tg_id = ?""",
                                (failed_login_attempts + 1, tg_id))
                else:
                    msg = send_tg_message(tg_id, 'Аутентификация в ЛК для работы с посещаемостью не удалась. Возможно, '
                                                 'в базе хранятся неактуальные данные. \n\nКоличество неудачных входов '
                                                 'подряд больше трех, поэтому автонапоминание об отмечаемости '
                                                 'отключено.')
                    cur.execute("""UPDATE user_ids SET failed_login_attempts = ?, attendance_cron = ? WHERE tg_id = ?""",
                                (0, 0, tg_id))
                continue
            code, session = attendance.auth_in_attendance(session)
            if code != 200:
                if failed_login_attempts <= 2:
                    msg = send_tg_message(tg_id, 'Аутентификация в ИС Посещаемость для работы с посещаемостью не '
                                                 'удалась. Возможно, в базе хранятся неактуальные данные.')
                    cur.execute("""UPDATE user_ids SET failed_login_attempts = ? WHERE tg_id = ?""",
                                (failed_login_attempts + 1, tg_id))
                else:
                    msg = send_tg_message(tg_id, 'Аутентификация в ИС Посещаемость для работы с посещаемостью не '
                                                 'удалась. Возможно, в базе хранятся неактуальные данные. \n\n'
                                                 'Количество неудачных входов подряд больше трех, поэтому '
                                                 'автонапоминание об отмечаемости отключено.')
                    cur.execute(
                        """UPDATE user_ids SET failed_login_attempts = ?, attendance_cron = ? WHERE tg_id = ?""",
                        (0, 0, tg_id))
                continue
            code, time_data, user, checkin, alldata = attendance.get_info_from_attendance(session)

            for lesson_elem in checkin:
                time_start = time.strptime(lesson_elem['start'], '%Y-%m-%dT%H:%M:%S.000%z')
                time_end = time.strptime(lesson_elem['end'], '%Y-%m-%dT%H:%M:%S.000%z')
                day_class = time_start.tm_yday
                day_now = now_time.tm_yday

                if day_now == day_class and time_start <= now_time <= time_end:
                    # пока что так, в дальнейшем добавить кнопочки и сделать отмечалку посещаемости
                    send_tg_message(tg_id, f'У тебя сейчас пара {lesson_elem["lesson"]["shortTitle"]}. Не забудь '
                                           f'отметиться!')
    return 0


def initialization():
    global vk_session
    global vk

    vk_session = vk_api.VkApi(token=token)
    vk = vk_session.get_api()

    send_vk_message('Планировочный дед активирован', 2000000001)
    send_tg_message(tg_admin_chat, 'Планировочный дед активирован')
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

# отмечалка посещаемости:
for time_element in timetable:
    schedule.every().day.at(time_element).do(attendance_schedule)

try:
    while True:
        schedule.run_pending()
        time.sleep(30)
except Exception as e:
    global_err = f'Произошла ошибка при выполнении cron_table: {str(e)}\n{traceback.format_exc()}'
    send_vk_message(global_err, 2000000001)
    send_tg_message(tg_admin_chat, global_err)
