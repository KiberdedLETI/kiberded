#! /usr/bin/env python
# -*- coding: utf-8 -*-
# dependencies: [scheduler]

import random
from datetime import date, datetime, timedelta
import sqlite3
import os
from shiza.databases_shiza_helper import create_database, remove_old_data
from shiza.etu_parsing import parse_exams, get_exam_data


path = f'{os.path.abspath(os.curdir)}/'
num_of_base = 589999  # объем базы анекдотов


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
        if today+timedelta(days=20) >= semester_end and today <= exam_end:
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
                               f'чат-бота.\n\nУдачи!\n'
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
