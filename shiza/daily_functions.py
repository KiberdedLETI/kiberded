#! /usr/bin/env python
# -*- coding: utf-8 -*-
# dependencies: [scheduler]

import random
from datetime import date, datetime, timedelta
from bot_functions.bots_common_funcs import day_of_day_toggle, weekly_toast_toggle
import sqlite3
import os
from shiza.databases_shiza_helper import create_database, remove_old_data
from shiza.etu_parsing import parse_exams, parse_group_params, get_exam_data
import toml
import sys


path = f'{os.path.abspath(os.curdir)}/'
num_of_base = 589999  # объем базы анекдотов


def get_day_photo() -> str:
    """
    Получение рандомной ссылки на фотографию для донатного ежедневного сообщения расписания в беседу
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

        # todo replace with fetchall()
        for row in cursor.execute(f'SELECT * FROM {source}_users'):
            data.append(tuple((int(row[0]), int(row[1]))))
        # \
    con.close()
    return data


def get_user_table_ids(source='vk') -> dict:  # список юзеров для рассылки расписания
    """
    Получение списка пользователей, подписанных на ежедневное расписание, а также параметров рассылки
    :param str source: 'vk' / 'tg' - источник сообщения

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


def get_groups():
    """
    Получение списка групп, ссылок на календарь и chat_ids
    :return: lists: groups, gcal_links, chat_ids, tg_chat_ids, tg_last_messages
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        con.row_factory = lambda cur, row: row[0]
        cur = con.cursor()
        groups = cur.execute('SELECT group_id FROM group_gcals').fetchall()
        gcal_links = cur.execute('SELECT gcal_link FROM group_gcals').fetchall()
        chat_ids = cur.execute('SELECT chat_id FROM group_gcals').fetchall()
        tg_chat_ids = cur.execute('SELECT tg_chat_id FROM group_gcals').fetchall()
        tg_last_messages = cur.execute('SELECT tg_last_msg FROM group_gcals').fetchall()  # Чтобы откреплять
    con.close()
    return groups, gcal_links, chat_ids, tg_chat_ids, tg_last_messages


def daily_cron(group):
    """
    Ежедневная проверка состояния группы (is_Study, is_Exam) с сопутствующим запуском разных функций парсинга данных

    :param group: группа
    :return: is_exam, is_study (bool 0/1), сообщение с оповещением об изменении
    """

    # также парсит периодически расписание на предмет обновлений.
    today = date.today()
    daily_return_str = ''

    # достаем из БД параметры "идет ли семестр" и "идет ли сессия"
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        all_dates = cur.execute(f'SELECT group_id, semester_start, semester_end, exam_end, isStudy, isExam '
                                f'FROM group_gcals WHERE group_id=?', [group]).fetchall()[0]

    # переводим в дату, чтобы можно было сравнить
    semester_start = datetime.strptime(all_dates[1], '%Y-%m-%d').date()
    semester_end = datetime.strptime(all_dates[2], '%Y-%m-%d').date()
    is_study_old = all_dates[4]
    is_exam_old = all_dates[5]

    # обновляем bool isStudy и isExam
    is_study = 1 if semester_start <= today < semester_end else 0
    if all_dates[3]:  # если есть даты экзамена
        exam_end = datetime.strptime(all_dates[3], '%Y-%m-%d').date()
        is_exam = 1 if semester_end <= today <= exam_end else 0  # обновляем данные

        # если семестр скоро закончится, пробуем подтянуть данные сессии
        if today+timedelta(days=30) >= semester_end and today <= exam_end:
            exam_data = get_exam_data(group)
            if exam_data:
                is_exam = 1
    else:
        is_exam = 0

    # записываем новые is_study и is_exam
    with con:
        cur.execute("UPDATE group_gcals SET isStudy=?, isExam=? WHERE group_id=?", [is_study, is_exam, group])
    con.close()

    # обновляем расписон сессии на всякий случай, еженедельно (в период сессии)
    if is_exam == is_exam_old == 1 and today.weekday() == 2 and is_exam:
        daily_return_str += parse_exams(group)  # если идет сессия, периодически обновляем расписание экзов
    # пытаемся (чуть-чуть) заранее подгружать данные до начала семестра/сессии todo
    #if semester_start-timedelta(days=2) <= today:  # осенью эт получается 30-08, зимой ~ начало февраля, норм
        #parse_group_params(group)  # пытаемся заранее подгружать даты нового сема
    if semester_end-timedelta(days=5) <= today:  # пытаемся заранее подгружать расписон сессии
        daily_return_str += parse_exams(group)  # если что, группа узнает о появившемся расписоне сессии

    # дальше реакции на 4 варианта изменения параметров - началась сессия/конец сессии, начался сем/конец сема*
    if is_exam != is_exam_old:
        if is_exam:  # если начались экзамены
            session_str = parse_exams(group)
            daily_return_str = f'Скоро сессия! Выживут не все, но будет весело.\n{session_str}\n' \
                               f'Расписание экзаменов всегда можно посмотреть во вкладке "Расписание" ' \
                               f'чат-бота.\nОбычное расписание отключено до следующего семестра\n\nУдачи!\n'
        else:  # если кончились экзамены
            parse_exams(group, set_default_next_sem=True)  # удаляем расписон экзаменов
            parse_group_params(group, set_default_next_sem=True)  # ставим датой начала сема дефолтный следующий
            daily_return_str = f'С окончанием сессии! До встречи в следующем семестре. ' \
                               f'А пока, Дед переходит в спящий режим.'

    if is_study != is_study_old:
        if is_study:  # если начался семестр
            # os.remove(f'{path}databases/{group}.db')  # стираем старые БД; генерируем новое.
            refresh_db_status, admin_book_str = create_database(group, keep_old_data_override=True, override_bool=True)
            parse_group_params(group)
            daily_return_str = f'С началом семестра! Теперь Дед будет ежедневно присылать утром расписание' \
                               f' на день.\nРасписание, список предметов и преподавателей, а также всякие' \
                               f' методички всегда можно посмотреть в чат-боте.\nУспехов!\n{refresh_db_status}\n' \
                               f'P.S. Методички предыдущего семестра, при наличии, должны быть доступны ближайший ' \
                               f'месяц, специально для любителей допсы.'
        else:  # если кончился семестр
            if not is_exam:  # если при этом сессии нету
                daily_return_str = 'С окончанием семестра! Дед переходит в спящий режим, расписания больше не будут ' \
                                   'присылаться. \nУдачи!'
            # *) кончился семестр, но началась сессия (is_exam смотрит на semester_end, так что она начинается сразу),
            # сообщение придет оттуда.

    if is_study and today-timedelta(days=28) >= semester_start:  # если кончилась допса
        data_removed = remove_old_data(group)
        if data_removed:
            daily_return_str = f'Из базы данных удалены методички предыдущего семестра.\nКто не закрылся - F.'

    if daily_return_str:
        daily_return_str += f'\n'  # форматирование итогового сообщения
    return is_exam, is_study, daily_return_str


def get_exam_notification(group, day=date.today()) -> str:
    """
    Достает экзамен на заданный день из таблицы с ними (при наличии оной)

    :param group: группа
    :param day: datetime.date
    :return: сообщение с расписанием
    """

    exam_day = str(day)
    if day == date.today():
        str_to_vk = 'Сегодня'
    elif day == date.today()+timedelta(days=1):
        str_to_vk = 'Завтра'
    else:
        str_to_vk = exam_day
    with sqlite3.connect(f'{path}databases/{group}.db') as con:
        cur = con.cursor()
        if cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exam_schedule'").fetchone() is None:
            return str_to_vk  # если нету таблицы с экзаменами, то ничего не присылаем todo pass
        else:
            exam = cur.execute('SELECT * FROM exam_schedule WHERE date=?', [exam_day]).fetchone()
            if exam is not None:
                str_to_vk += f' в {exam[1]} экзамен по {exam[2]}\nПреподаватель - {exam[3]}' \
                             f'\nАудитория {exam[4]}\nУдачи!'
                return str_to_vk

            else:  # консультации
                consult = cur.execute('SELECT * FROM exam_schedule WHERE consult_date=?', [exam_day]).fetchone()
                if consult is not None:
                    str_to_vk += f' в {consult[6]} консультация по {consult[2]}\nПреподаватель - {consult[3]}'
                    if consult[7] != '':
                        str_to_vk += f'\nАудитория {consult[7]}'
                    return str_to_vk
    return ''


def donator_daily_cron(group) -> str:  # все, что относится к донатам и особому, донатному функционалу
    """
    Донатный функционал - это случайная картинка а-ля паблик "с днем поздравляющих животных".
    Донатный он потому, что это вещь на любителя, так что не хотели всем такое давать...

    :param group: группа
    :return: (при наличии) оповещение об истечении донатного периода; ссылка на картинку (тоже при наличии)
    """

    today = date.today()
    donator_message = ''
    attach = ''

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        last_donate = cur.execute("SELECT last_donate FROM group_gcals WHERE group_id=?", [group]).fetchone()[0]  # 0/1

        if last_donate:  # если есть инфо о донате
            donate_date = datetime.strptime(last_donate, '%Y-%m-%d').date()  # переводим в дату

            if today > donate_date:  # донат уже не в силе
                # todo: сделать включение донатов разовым; пока что можно просто задать огромный срок истечения вручную

                # сбрасываем дату, чтобы не спамить уведомлениями о закончившемся донате
                cur.execute('UPDATE group_gcals SET last_donate=null WHERE group_id=?', [group])
                with_dayofday, with_toast = cur.execute("SELECT with_dayofday, with_toast FROM group_gcals WHERE group_id=?", [group]).fetchone()

                if with_dayofday:  # если были подключены пикчи
                    day_of_day_toggle(group)
                    donator_message += 'Ежедневные пикчи отключены. Чтобы снова видеть это безобразие, ' \
                                       'заплатите чеканной монетой - зачтется все это вам!'

                if with_toast:  # если были подключены тосты
                    weekly_toast_toggle(group)
                    donator_message += '\nКажется, деду стало нечем похмеляться - тосты отключены.'
                else:
                    donator_message = 'Истек срок подключения функций для донатеров.'

            # если донат в силе
            elif today <= donate_date:
                attach = get_day_photo()

    con.close()
    if donator_message:
        donator_message = f'{donator_message}\n'  # форматирование сообщения
    return donator_message, attach
