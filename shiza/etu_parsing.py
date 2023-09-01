# dependencies: [chat_bot, telegram_bot, scheduler]
"""
Парсинг данных с api ИС "Расписание" ЛЭТИ, а также настройка бота - учебный/сессионный/каникулярный режимы в группе

Полезные ссылки (потому что ЛЭТИ все никак не напишет документацию своей апишки):
    расписание во вкладке преподы + отдельно кнопка преподы во вкладке "расписание"
    https://digital.etu.ru/schedule/?department=каф.Физики&initials=Харитонский+Петр+Владимирович&schedule=teacher
    https://digital.etu.ru/schedule/?department={departament}&initials={surname}+{name}+{midname}&schedule=teacher

    https://digital.etu.ru/api/schedule/objects/publicated?anyTeacherId=906&noEmptyGroups=true&withSubjectCode=true&withURL=true&forLastPublicatedSchedule=true

    https://digital.etu.ru/api/general/dicts/teachers - все преподы:
        initials, name, surname, midname, id, roles(list)

    https://digital.etu.ru/api/general/dicts/departments - все кафедры:
        id, title, type(??), faculty_id

    https://digital.etu.ru/api/general/dicts/teachers?departmentId=departamentId - преподы кафедры:
        initials, name, surname, midname, id, roles(list)

Другие интересные endpoint-ы
    https://digital.etu.ru/api/general/current - текущая дата, четность, семестр
"""

import json
import os
import re
import time
import pandas as pd
import sqlite3
import requests
from datetime import datetime, date, timedelta
import recurring_ical_events
from icalendar import Calendar
import pytz


days = [['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'], [' (чёт)', ' (нечёт)']]
lesson_numbers_allowed = ['1', '2', '3', '4', '5', '6', '7', '8']
parity_allowed = ['0', '1']
timetable = ['08:00', '09:50', '11:40', '13:40', '15:30', '17:20', '19:05', '20:50']
path = f'{os.path.abspath(os.curdir)}/'
today = date.today()
tomorrow = today + timedelta(days=1)
lesson_length = 90

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'}


def get_departments_data() -> pd.DataFrame:
    """
    Заглядывает в раздел с кафедрами, возвращает его данные
    :return: DataFrame [['id', 'title', 'type', 'facultyId']]
    """

    # Получение данных
    try:
        url = 'https://digital.etu.ru/api/general/dicts/departments'
        df = pd.DataFrame(requests.get(url, headers=headers).json())
        df = df[['id', 'title', 'type', 'facultyId']].set_index('id')
        df['facultyId'] = df['facultyId'].fillna(0)
        if df.empty:
            raise ValueError('Не удалось получить данные о кафедрах (general/dicts/departments)')
    except Exception as data_err:
        raise ValueError(f"Неизвестная ошибка получения данных departments: {data_err}")
    return df


def parse_prepods_db():
    """
    Создает и заполняет таблицы departments, prepods в БД prepods.db
    :return: 0
    """

    insert_data = pd.DataFrame(columns=['id', 'dep_id', 'initials', 'name', 'surname', 'midname', 'roles'])
    departments_data = get_departments_data()

    for dep in departments_data.index.tolist():
        url = f'https://digital.etu.ru/api/general/dicts/teachers?departmentId={dep}'
        data = requests.get(url, headers=headers).json()

        for d in data:
            if not isinstance(d, dict):
                continue
            initials = d['initials']
            name = d['name']
            surname = d['surname']
            midname = d['midname']
            if not re.search(r'[a-zA-Zа-яА-Я]', midname):
                midname = None

            id = d['id']  # по нему быстрее искать расписание
            roles = ', '.join([el for el in d['roles']])

            insert_data.loc[len(insert_data)] = [id, dep, initials, name, surname, midname, roles]

    insert_data = list(insert_data.itertuples(index=False, name=None))

    with sqlite3.connect(f'{path}admindb/databases/prepods.db') as con:
        cur = con.cursor()

        # Заполнение таблицы departments
        cur.execute('CREATE TABLE IF NOT EXISTS '
                    'departments (id INTEGER PRIMARY KEY, title TEXT, type TEXT, facultyId INTEGER)')
        cur.execute('DELETE FROM departments')
        departments_data.to_sql('departments', con, if_exists='append')  # appending to empty table to keep PK
        con.commit()

        # Заполнение таблицы prepods
        cur.execute('CREATE TABLE IF NOT EXISTS prepods (id integer, department_id integer, '
                    'initials text, name text, surname text, midname text, roles text)')
        cur.execute('DELETE FROM prepods')
        cur.executemany('INSERT INTO prepods VALUES (?, ?, ?, ?, ?, ?, ?)', insert_data)
        con.commit()
    con.close()
    return 0


def parse_prepods_schedule_from_ics(url):
    """
    Парсер расписания преподов из .ics файла
    :param url:
    :return:
    """
    data_from_url = requests.get(url, headers=headers).text.encode('iso-8859-1')  # тут чето может сломаться
    data_ics = data_from_url.decode('utf-8').replace('\\r\\', '')

    if not data_ics:
        print('No data from url')
        return pd.DataFrame()

    full_cal = Calendar.from_ical(data_ics)

    # todo replace with parity source from API?
    parity_count = []  # костыль для проверки четности, сравнение с первой неделей (первой парой) сема
    for component in full_cal.walk():
        if component.get('dtstart'):
            dtstart_par = component.get('dtstart').dt
            parity_count.append(dtstart_par)
    parity_count.sort()

    schedule_list = []
    for i in range(14):
        day = datetime.now(pytz.timezone('Europe/Moscow')).date() + timedelta(days=i)
        for component in full_cal.walk():
            if component.get('dtstart'):

                dtstart = component.get('dtstart').dt
                if (day.isocalendar()[1] - dtstart.isocalendar()[1]) % 2 == 0 and dtstart.weekday() == day.weekday():
                    if (day.isocalendar()[1] - parity_count[0].isocalendar()[1]) % 2 == 0:
                        parity = '1'  # если криво меняется на "% 2 != 0" строкой выше
                    else:
                        parity = '0'
                    dtstart = str(dtstart).split()[1][:5]

                    # Название сокращенно
                    summary = component.get('SUMMARY').split()

                    subject = ' '.join(summary[:-1])
                    subject_type = summary[-1]

                    # Описание (полное название, аудитория, группы)
                    description = component.get('DESCRIPTION')
                    description = description.split('\n\n')

                    # Аудитория
                    classroom = ''
                    description_classroom = description[0].split()[0]
                    if description[0][:2] == "a." or description[0][:2] == "а." and  \
                            any(char.isdigit() for char in description_classroom):
                        classroom = description_classroom[2:].strip(',')
                        description[0] = ' '.join(description[0].split()[1:])
                    if len(description) > 2:
                        if 'Дистанционн' in description[2]:
                            classroom = '(Дист.)'

                    full_subject = description[0]
                    # 'Период 2022-09-01 - 2022-12-30: 8373, 8374' -> '8373, 8374'
                    groups = description[1].split(':')[-1].strip()
                    # Альтернатива
                    # remove '\n\nПериод 2022-09-01 - 2022-12-30: 8373, 8374' from description (second_element)
                    # description = re.sub(r'Период \d{4}-\d{2}-\d{2} - \d{4}-\d{2}-\d{2}', '', description)

                    try:
                        lesson_number = timetable.index(dtstart)
                        lesson_number += 1  # тупейший фикс, чтобы было все понятнее в экселе
                    except ValueError:
                        lesson_number = dtstart

                    schedule_list.append([days[0][day.weekday()], parity, lesson_number, subject, full_subject,
                                          subject_type, classroom, groups])
    # перенос в датафрейм
    schedule = pd.DataFrame(schedule_list,
                            columns=['weekday', 'parity', 'lesson_number', 'subject', 'subject_full', 'subject_type',
                                     'classroom', 'groups'],
                            dtype=str)
    schedule[schedule.columns] = schedule.apply(lambda x: x.str.strip())  # убираем гадости в виде пробелов
    return schedule


def parse_prepods_schedule():
    """
    Заполняет таблицу schedule БД prepods.db

    :param int department_id: айди кафедры
    :param int id: айди препода
    :return:
    """

    with sqlite3.connect(f'{path}admindb/databases/prepods.db') as con:
        cur = con.cursor()
        data = cur.execute('SELECT id, initials FROM prepods ORDER BY id').fetchall()

        cur.execute('DROP TABLE IF EXISTS schedule')
        cur.execute('CREATE TABLE IF NOT EXISTS schedule '
                    '(weekday TEXT, parity INTEGER, lesson_number INTEGER, subject TEXT, subject_type TEXT, '
                    'classroom TEXT, full_subject , teacher	TEXT, teacher_id INTEGER SECONDARY KEY, groups TEXT)')
        con.commit()
    con.close()

    q = 'INSERT INTO schedule ' \
        '(weekday, parity, lesson_number, subject, subject_type, full_subject, classroom, teacher, teacher_id, groups)' \
        ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'

    # Перезапуск заполнения, если while не устраивает
    # restart = [d[1] for d in data].index('Фамилия И.О.')
    # data = data[restart:]

    for d in data:
        print(d[1])
        ics_url = f'https://digital.etu.ru/api/schedule/ics-export/teacher?anyTeacherId={d[0]}&scheduleId=publicated'

        loaded = False
        while not loaded:
            try:
                df = parse_prepods_schedule_from_ics(ics_url)
                loaded = True
            except Exception as e:
                print(f'Ошибка парсинга: {e}')
                time.sleep(10)

        if df.empty:
            print('Пусто')
            continue

        df['teacher'] = d[1]
        df['teacherId'] = d[0]

        # Заполнение
        with sqlite3.connect(f'{path}admindb/databases/prepods.db') as con:
            cur = con.cursor()
            ins_data = list(df[['weekday', 'parity', 'lesson_number', 'subject', 'subject_type', 'subject_full',
                                'classroom', 'teacher', 'teacherId', 'groups']].itertuples(index=False, name=None))
            # print(ins_data)
            cur.executemany(q, ins_data)
            con.commit()
        con.close()
    return 0


def get_calendar(group_id, day=today) -> str:
    """
    Составление расписания из .ical календаря

    :param str group_id: номер группы
    :param day: datetime.date
    :return: сообщение с расписанием
    """

    # Получение ссылки на календарь
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        url = cur.execute("SELECT gcal_link FROM group_gcals WHERE group_id=?", [group_id]).fetchone()
    con.close()
    if url:  # если не пусто
        url = url[0]
    else:
        return f'Ошибка: календарь группы {group_id} не найден.'

    # Получение json с календарем
    try:
        gcal = recurring_ical_events.of(Calendar.from_ical(requests.get(url).text)).at(day)
    except Exception:
        return f'Ошибка доступа к календарю {group_id}. Проверьте работоспособность загруженной ссылки'

    answer = f'Расписание на {str(day)}'
    clean_gcal = []  # чтобы убрать "выезжающие" ивенты на весь день

    # Парсинг в сообщение
    for event in gcal:
        # Честно сказать, я не помню что тут происходит...
        dtstart = event['DTSTART']
        if len(str(dtstart.dt)) < 11 and dtstart.dt == day:
            dtstart.dt = datetime.combine(day, datetime.min.time())
            event['DTSTART'] = str(dtstart.dt)[11:16]
            clean_gcal.append(event)
        elif len(str(dtstart.dt)) > 13:
            dtstart.dt = pytz.timezone('Europe/Moscow').normalize(dtstart.dt)
            event['DTSTART'] = str(dtstart.dt)[11:16]
            clean_gcal.append(event)
    clean_gcal.sort(key=lambda x: x['dtstart'])  # сортирооооооооооовка

    # Сборка данных в сообщение
    for event in clean_gcal:
        dtstart = event["DTSTART"]  # время начала ивента
        summary = event['SUMMARY']  # название
        try:
            description = event['DESCRIPTION']  # описание
        except KeyError:
            description = ''

        answer += '\n' + '\n' + summary

        if 'https' in description:  # обработка ссылок в сообщении (нормально работает только с одной ссылкой)
            # todo можно сделать обработку нескольких ссылок
            link = re.search("(?P<url>https?://[^\s'\"]+)", description).group("url")
            description = description.replace(link, '')
            description = description.replace('<br>', '\n')
            clean = re.compile('<.*?>')
            description = re.sub(clean, '', description)
            answer += f'\nСсылка: {link}'

        if description != '':  # описание ивента
            answer += f'\nОписание: {description}'

        if dtstart != '00:00':  # время начала
            answer += f'\nНачало: {dtstart}'

    if answer == f'Расписание на {str(day)}':
        answer += '\nПусто'
    return answer


def load_calendar_cache(group=None):
    """
    Загрузка календарей всех групп в кэш-базу, чтобы ускорить доступ к ним. Запихнул пока сюда, не знаю куда еще...

    :param group: (опционально) номер группы. Если нет - обновляет все группы
    :return:
    """

    if group is not None:
        groups = [group]
    else:
        with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
            cur = con.cursor()
            groups = cur.execute("SELECT group_id FROM group_gcals WHERE gcal_link IS NOT NULL").fetchall()
        con.close()
        groups = list(set([gr[0] for gr in groups]))

    # Создаем директории для кэша
    if not os.path.exists(f'{path}cache/'):
        os.mkdir(f'{path}cache/')
    if not os.path.exists(f'{path}cache/'):
        os.mkdir(f'{path}cache/')

    # Создаем таблицу и выгружаем кэш в нее
    with sqlite3.connect(f'{path}cache/calendar_cache.db') as con:
        cur = con.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS '
                    'calendar_cache (group_id TEXT NOT NULL PRIMARY KEY, today TEXT, tomorrow TEXT)')
        con.commit()

        # Очищаем кэш по заданным группам
        cur.execute('DELETE FROM calendar_cache WHERE group_id IN ({})'.format(','.join(groups)))
        con.commit()

        for group in groups:
            print(group)
            cal_today = get_calendar(group, today)
            cal_tomorrow = get_calendar(group, tomorrow)

            cur.execute(f"INSERT INTO calendar_cache (group_id, today, tomorrow) "
                        f"VALUES (?, ?, ?)",
                        (group, cal_today, cal_tomorrow))
        con.commit()
    con.close()
    return 0


def get_group_schedule_from_ics(group, publicated=True):
    """
    Парсер расписания группы из .ics с digital.etu.ru/schedule

    :param str group: номер группы (обычный, не etu_id)
    :param bool publicated: if False, выгружает предварительное расписание (при наличии)
    :return: 2 DataFrame - schedule / prepods для загрузки в базу
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:  # достаем странный айдишник
        cur = con.cursor()
        etu_id = cur.execute("SELECT etu_id FROM group_gcals WHERE group_id=?", [group]).fetchone()
        if etu_id:  # если группа такая существует
            etu_id = etu_id[0]
    con.close()

    try:  # парсер в расписон и преподов
        url = (f'https://digital.etu.ru/api/schedule/ics-export/group?'
               f'groups={etu_id}{"&scheduleId=publicated" if publicated else ""}')
        try:
            data_from_url = requests.get(url, headers=headers).text.encode('iso-8859-1')  # тут чето может сломаться
            data_ics = data_from_url.decode('utf-8').replace('\\r\\', '')
            full_cal = Calendar.from_ical(data_ics)
        except requests.exceptions.ConnectTimeout:
            time.sleep(5)
            data_from_url = requests.get(url, headers=headers).text.encode('iso-8859-1')
            data_ics = data_from_url.decode('utf-8').replace('\\r\\', '')
            full_cal = Calendar.from_ical(data_ics)
        except ValueError:
            return f'Отсутствует расписание {group}\n', ''

        parity_count = []  # костыль для проверки четности, сравнение с первой неделей (первой парой) сема
        for component in full_cal.walk():
            if component.get('dtstart'):
                dtstart_par = component.get('dtstart').dt
                parity_count.append(dtstart_par)
        parity_count.sort()

        schedule_list = []
        prepods_list = []

        for i in range(14):  # 14 - две недели, четная/нечетная
            day = datetime.now(pytz.timezone('Europe/Moscow')).date() + timedelta(days=i)
            for component in full_cal.walk():
                if component.get('dtstart'):
                    dtstart = component.get('dtstart').dt
                    if (day.isocalendar()[1] - dtstart.isocalendar()[1]) % 2 == 0 and dtstart.weekday() == day.weekday():

                        if (day.isocalendar()[1] - parity_count[0].isocalendar()[1]) % 2 == 0:  # Чётность пары
                            parity = '1'  # если криво меняется на "% 2 != 0" строкой выше
                        else:
                            parity = '0'

                        dtstart = str(dtstart).split()[1][:5]
                        summary = component.get('SUMMARY').split()
                        description = component.get('DESCRIPTION')

                        name = 'Ошибка ФИО'  # ФИО преподавателя
                        classroom = ''  # может сломаться?
                        subject = ' '.join(summary[:-1])
                        full_subject = ''  # полное название предмета
                        subject_type = summary[-1]

                        if description != '':  # достаем аудиторию и ФИО преподавателя
                            description_comma_split = description.split(',')
                            description = description.split('\n')
                            full_subject = description[1]
                            if any(char.isdigit() for char in description_comma_split[0]) is True:
                                classroom = description_comma_split[0]
                                description[0] = ' '.join(description[0].split()[1:])
                                name = description[0]
                            elif description[-1] == 'Форма обучения: Дистанционная':
                                classroom = 'дистанционно'
                                name = description[0]

                            if description[0] == 'Преподаватель не назначен':
                                name = description[0]
                        try:
                            lesson_number = timetable.index(dtstart)
                            lesson_number += 1  # тупейший фикс, чтобы было все понятнее в экселе
                        except ValueError:
                            lesson_number = dtstart

                        prepods_list.append([subject, subject_type, full_subject, name])
                        schedule_list.append(
                            [days[0][day.weekday()], parity, lesson_number, subject, subject_type,
                             full_subject, name, classroom])
        # перенос в датафрейм
        schedule = pd.DataFrame(schedule_list,
                                columns=['weekday', 'parity', 'lesson_number', 'subject', 'subject_type',
                                         'full_subject', 'teacher', 'classroom'],
                                dtype=str)
        schedule[schedule.columns] = schedule.apply(lambda x: x.str.strip())  # убираем гадости в виде пробелов

        prepods = pd.DataFrame(prepods_list, columns=['subject', 'subject_type', 'full_subject', 'name'], dtype=str)
        prepods[prepods.columns] = prepods.apply(lambda x: x.str.strip())
        prepods = prepods.drop_duplicates()

    except Exception as e:
        return str(e), ''

    return schedule, prepods


def get_table(group=None, day=None, teacher_id=None, type='short') -> str:
    """
    Получение сообщения с расписанием из БД
    todo 2 варианта расписания - полное и сокращенное

    :param group: номер группы
    :param day: Понедельник (чёт) и т.д.
    :param teacher_id: если True - возвращает расписание преподавателя на заданный день
    :param str type: тип расписания ('short' или 'full', названия предметов)
    :return: сообщение с расписанием
    """

    db_path = f'{path}databases/{group}.db' if not teacher_id else f'{path}admindb/databases/prepods.db'

    # принимает день (например: day = 'Среда (чёт), По умолчанию на сегодня - для крона', возвращает расписание из БД.
    str_to_vk = f'Расписание на: {day}'
    con = sqlite3.connect(db_path)

    cursor = con.cursor()
    parity = '1' if day.split()[-1] == '(нечёт)' else '0'
    weekday = str(day.split()[0])
    prev_start_time = ''
    prev_data = []

    q_add = '' if not teacher_id else f'AND teacher_id = {teacher_id}'
    subj = 'subject' if type == 'short' else 'subject_full'  # todo

    try:
        # Построчно добавляем каждую пару на заданный день в сообщение с расписанием
        for row in cursor.execute(f"SELECT weekday, parity, lesson_number, subject, subject_type, classroom "
                                  f"FROM schedule "
                                  f"WHERE weekday=? AND parity=? {q_add} "
                                  f"ORDER BY lesson_number ASC", (weekday, parity)):

            start_time_str = timetable[int(row[2])-1]  # время начала пары
            lesson_data = [row[3], row[4], row[5]]  # предмет, тип занятия, аудитория
            str_to_vk += '\n'

            if prev_start_time:  # сравниваем с предыдущим началом пары и смотрим, есть ли окно и какое оно
                start_time = datetime.strptime(start_time_str, '%H:%M')
                prev_start_time = datetime.strptime(prev_start_time, '%H:%M')

                # Если начало пары больше чем (начало предыдущей+длина пары+перерыв 30 минут), добавляем пропуск строки
                if start_time >= prev_start_time + timedelta(minutes=(lesson_length+30)):
                    lesson_window = str(start_time - timedelta(minutes=lesson_length) - prev_start_time)
                    lesson_window = datetime.strftime(datetime.strptime(lesson_window, '%H:%M:%S'), '%H:%M')
                    str_to_vk += f'\n{str((prev_start_time+timedelta(minutes=lesson_length)).time())[:-3]} - ' \
                                 f'{datetime.strftime(start_time, "%H:%M")} - Перерыв {lesson_window}\n\n'

                # Иначе, если время начала совпадает с предыдущей парой, пишем на соседних строках
                elif start_time == prev_start_time:

                    # Если совпадает предмет и тип занятия (отличаются аудитории), пишем без дубликата названия предмета
                    if lesson_data[0] == prev_data[0] and lesson_data[1] == prev_data[1]:
                        if not lesson_data[-1]:  # Если по первому нет аудитории, пишем по второму
                            prev_data = lesson_data[:-1] + [prev_data[-1]]
                        elif prev_data[-1]:  # Пустую аудиторию не пишем
                            prev_data = lesson_data + ['|'] + [prev_data[-1]]  # добавляем еще один номер аудитории
                    else:
                        prev_data = lesson_data + ['|'] + prev_data

                    str_to_vk = str_to_vk[:str_to_vk.rfind('\n', 0, str_to_vk.rfind('\n'))]
                    str_to_vk += f'\n{start_time_str} - {" ".join(prev_data)}'
                    prev_start_time = start_time_str
                    continue

            prev_start_time = start_time_str
            prev_data = lesson_data
            str_to_vk += f'{start_time_str} - {row[3]} {row[4]} {row[5]}'

        if str_to_vk == f'Расписание на: {day}':
            str_to_vk += '\nПусто'
            return str_to_vk

    except Exception as e:
        str_to_vk += f'\nОшибка расписания: {e}'
    con.close()

    return str_to_vk


def load_table_cache(group=None):
    """
    Загрузка расписаний всех групп в кэш-базу, чтобы ускорить доступ к ним (примерно на 2 мс...).
    Запихнул пока сюда, не знаю куда еще...

    :param group: (опционально) номер группы. Если нет - обновляет все группы
    :return:
    """

    days_0 = ['Понедельник (чёт)',
              'Вторник (чёт)',
              'Среда (чёт)',
              'Четверг (чёт)',
              'Пятница (чёт)',
              'Суббота (чёт)',
              'Воскресенье (чёт)']
    days_1 = ['Понедельник (нечёт)',
              'Вторник (нечёт)',
              'Среда (нечёт)',
              'Четверг (нечёт)',
              'Пятница (нечёт)',
              'Суббота (нечёт)',
              'Воскресенье (нечёт)']

    if group:
        groups = [group]
    else:
        with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
            cur = con.cursor()
            groups = cur.execute('SELECT group_id FROM group_gcals').fetchall()
            groups = [group[0] for group in groups]
        con.close()

    for group in groups:
        print(group)

        if not os.path.exists(f'{path}databases/{group}.db'):
            print(f'{group} not found')
            continue

        with sqlite3.connect(f'{path}/databases/{group}.db') as con:
            cur = con.cursor()
            cur.execute('CREATE TABLE IF NOT EXISTS table_cache (`day` TEXT NOT NULL PRIMARY KEY, `day_table` TEXT)')
            con.commit()

            cur.execute('DELETE FROM table_cache')
            con.commit()

            # Четная неделя
            full_table = f'Расписание {group} на неделю (чётная): \n'  # Вся неделя
            for day in days_0:
                data = get_table(group, day)

                if data.split('\n')[-1] == 'Пусто' and len(data.split('\n')) == 2:
                    pass
                else:
                    # убираем строку с перерывом из этого расписания
                    day_data = re.sub(r'(\n\d{2}:\d{2} - \d{2}:\d{2} - Перерыв \d{2}:\d{2}\n\n)', '', data)
                    full_table += f"\n{day_data.replace('Расписание на: ', '').replace(' (чёт)', '')}\n"

                cur.execute(f"INSERT INTO table_cache (day, day_table) VALUES (?, ?) ", (day, data,))

            if full_table == f'Расписание {group} на неделю (чётная): \n':
                full_table = f'Расписание {group} на неделю (чётная): \nПусто'
            cur.execute(f"INSERT INTO table_cache (day, day_table) VALUES (?, ?) ", ('full (чёт)', full_table,))

            # Нечётная неделя
            full_table = f'Расписание {group} на неделю (нечётная): \n'  # Вся неделя
            for day in days_1:
                data = get_table(group, day)
                if data.split('\n')[-1] == 'Пусто' and len(data.split('\n')) == 2:
                    pass
                else:
                    # убираем строку с перерывом из этого расписания
                    day_data = re.sub(r'(\n\d{2}:\d{2} - \d{2}:\d{2} - Перерыв \d{2}:\d{2}\n\n)', '', data)
                    full_table += f"\n{day_data.replace('Расписание на: ', '').replace(' (нечёт)', '')}\n"

                cur.execute(f"INSERT INTO table_cache (day, day_table) VALUES (?, ?) ", (day, data,))

            if full_table == f'Расписание {group} на неделю (нечётная): \n':
                full_table = f'Расписание {group} на неделю (нечётная): \nПусто'
            cur.execute(f"INSERT INTO table_cache (day, day_table) VALUES (?, ?) ", ('full (нечёт)', full_table,))

            con.commit()
        con.close()

    print('Кэш расписаний загружен')
    return 0


def load_prepods_table_cache():
    """
    Загрузка расписаний всех преподавателей в кэш-базу, чтобы ускорить доступ
    :return:
    """

    days_0 = ['Понедельник (чёт)',
              'Вторник (чёт)',
              'Среда (чёт)',
              'Четверг (чёт)',
              'Пятница (чёт)',
              'Суббота (чёт)',
              'Воскресенье (чёт)']
    days_1 = ['Понедельник (нечёт)',
              'Вторник (нечёт)',
              'Среда (нечёт)',
              'Четверг (нечёт)',
              'Пятница (нечёт)',
              'Суббота (нечёт)',
              'Воскресенье (нечёт)']

    with sqlite3.connect(f'{path}admindb/databases/prepods.db') as con:
        cur = con.cursor()

        teachers = cur.execute('SELECT DISTINCT teacher_id, teacher FROM schedule ORDER BY teacher_id').fetchall()

        try:  # Не знаю почему это постоянно попадает сюда
            teachers.remove(('teacher_id', 'teacher'))
        except ValueError:
            pass

        cur.execute('CREATE TABLE IF NOT EXISTS table_cache '
                    '(`id` INTEGER, `name` TEXT, `day` TEXT, `day_table` TEXT, '
                    'PRIMARY KEY (`id`, `day`))')
        con.commit()

        cur.execute('DELETE FROM table_cache')
        con.commit()

        for teacher in teachers:
            teacher_id = teacher[0]
            teacher_name = teacher[1]
            print(teacher_id, teacher_name)

            # Четная неделя
            full_table = f'Расписание {teacher_name} на неделю (чётная): \n'  # Вся неделя
            for day in days_0:
                data = get_table(day=day, teacher_id=teacher_id)

                if data.split('\n')[-1] == 'Пусто' and len(data.split('\n')) == 2:
                    pass
                else:
                    # убираем строку с перерывом из этого расписания
                    day_data = re.sub(r'(\n\d{2}:\d{2} - \d{2}:\d{2} - Перерыв \d{2}:\d{2}\n\n)', '', data)
                    full_table += f"\n{day_data.replace('Расписание на: ', '').replace(' (чёт)', '')}\n"

                cur.execute(f"INSERT INTO table_cache (id, name, day, day_table) "
                            f"VALUES (?, ?, ?, ?) ", (teacher_id, teacher_name, day, data))

            if full_table == f'Расписание {teacher_name} на неделю (чётная): \n':
                full_table = f'Расписание {teacher_name} на неделю (чётная): Пусто'
            cur.execute(f"INSERT INTO table_cache (id, name, day, day_table) "
                        f"VALUES (?, ?, ?, ?) ", (teacher_id, teacher_name, 'full (чёт)', full_table))

            # Нечётная неделя
            full_table = f'Расписание {teacher_name} на неделю (нечётная): \n'  # Вся неделя (нечёт)
            for day in days_1:
                data = get_table(day=day, teacher_id=teacher_id)

                if data.split('\n')[-1] == 'Пусто' and len(data.split('\n')) == 2:
                    pass
                else:
                    # убираем строку с перерывом из этого расписания
                    day_data = re.sub(r'(\n\d{2}:\d{2} - \d{2}:\d{2} - Перерыв \d{2}:\d{2}\n\n)', '', data)
                    full_table += f"\n{day_data.replace('Расписание на: ', '').replace(' (нечёт)', '')}\n"

                cur.execute(f"INSERT INTO table_cache (id, name, day, day_table) "
                            f"VALUES (?, ?, ?, ?) ", (teacher_id, teacher_name, day, data))

            if full_table == f'Расписание {teacher_name} на неделю (нечётная): \n':
                full_table = f'Расписание {teacher_name} на неделю (нечётная): Пусто'
            cur.execute(f"INSERT INTO table_cache (id, name, day, day_table) "
                        f"VALUES (?, ?, ?, ?) ", (teacher_id, teacher_name, 'full (нечёт)', full_table))

            con.commit()
    con.close()
    return 0


def get_exam_data(group):
    """
    Получение расписания сессии с API ЛЭТИ

    :param str group: номер группы
    :return: JSON с данными или 0
    """

    return_str = {}

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        try:
            etu_id, course, study_type = \
                cur.execute("SELECT etu_id, course, studying_type FROM group_gcals WHERE group_id=?",
                            [group]).fetchall()[0]
        except IndexError:

            return {}
    con.close()

    url = f'https://digital.etu.ru/api/exams/objects?' \
          f'groupfacultyId={group[1]}&courses={course}&studyingType={study_type}' \
          f'&examId=publicated&withConsult=true&departmentId=all'  # group[1] - вторая цифра номера группы - факультет
    all_exams = requests.get(url, headers=headers).json()
    
    if not all_exams:  # возможно стоит сделать вторую попытку получения данных либо лог об ошибке
        return 0
    
    if not all_exams['examObjects']:
        return 0

    for i in range(len(all_exams['examObjects'])):  # собираем в кучу все данные для таблицы
        if str(all_exams['examObjects'][i]['groupId']) == etu_id:
            return_str[i] = all_exams['examObjects'][i]
    return_json = return_str
    return return_json


def parse_exams(group, set_default_next_sem=False):
    """
    Парсер расписания сессии

    :param group: группа
    :param set_default_next_sem: if True, чистит Деда от прошедшей сессии, и на этом все.
    :return: сообщение с оповещением об изменениях в беседу группы
    """

    return_data = ''  # Для крона, оповещения об изменениях в расписании сессии
    got_exams = False  # Флаг получения информации об экзаменах

    exam_json_data = get_exam_data(group)
    if not exam_json_data:
        return return_data, got_exams

    if set_default_next_sem:  # если кончилась сессия, стираем таблицу
        with sqlite3.connect(f'{path}databases/{group}.db') as con:
            cur = con.cursor()
            cur.execute('DROP TABLE IF EXISTS exam_schedule')
        con.close()
        return return_data, got_exams

    # Парсер JSON с данными
    with sqlite3.connect(f'{path}databases/{group}.db') as con:
        cur = con.cursor()
        cur.execute(
            'CREATE TABLE '
            'IF NOT EXISTS exam_schedule '
            '(date text, time text, subject text, name text, classroom text, '
            'consult_date text, consult_time text, consult_classroom text)')

        old_data = cur.execute('SELECT * FROM exam_schedule ORDER BY date').fetchall()
    new_data = []

    for i in exam_json_data:  # собираем в кучу все данные для таблицы
        exam_element = exam_json_data[i]
        start_date = str(exam_element['auditoriumReservation']['reservationTime']['startDate'])
        start_time = str(exam_element['auditoriumReservation']['reservationTime']['startTime'])[1:] + ':00'
        short_title = exam_element['subjectGroup']['subject']['shortTitle']
        auditorium_num = str(exam_element['auditoriumReservation']['auditoriumNumber'])
        if auditorium_num == 'None':
            auditorium_num = ''
        if exam_element['teacher'] is not None:
            teacher_surname = exam_element['teacher']['surname']
            teacher_name = exam_element['teacher']['name']
            teacher_midname = exam_element['teacher']['midname']
            teacher = f'{teacher_surname} {teacher_name} {teacher_midname}'
        else:
            teacher = ''

        # Данные по консультации при наличии
        consult_date = ''
        consult_start_time = ''
        consult_classroom = ''
        try:
            if exam_element['examConsultation']:
                consult_date = exam_element['examConsultation']['reservationTime']['startDate']
                consult_start_time = str(exam_element['examConsultation']['reservationTime']['startTime'])[1:] + ':00'
                consult_classroom = str(exam_element['examConsultation']['auditoriumReservation']['auditoriumNumber'])
        except (KeyError, TypeError):  # на всякий, если косяки в JSON-e
            pass

        # None меняем на всякий
        consult_classroom = consult_classroom if consult_classroom != 'None' else ''
        consult_date = consult_date if consult_date != 'None' else ''
        consult_start_time = consult_start_time if consult_start_time != 'None' else ''

        new_data += [(start_date, start_time, short_title, teacher, auditorium_num,
                      consult_date, consult_start_time, consult_classroom)]
        # инициалы, № ауд., дата экза, время экза (! нестабильно), название (если title в последнем арг. - полное)

    # Загрузка данных в БД
    with con:
        cur.execute('DROP TABLE IF EXISTS exam_schedule')
        if not new_data:  # если нет экзаменов
            return return_data, got_exams
        cur.execute('CREATE TABLE exam_schedule '
                    '(date text, time text, subject text, name text, classroom text, '
                    'consult_date text, consult_time text, consult_classroom text)')

        cur.executemany('INSERT INTO exam_schedule VALUES (?, ?, ?, ?, ?, ?, ?, ?)', new_data)
        new_data = cur.execute('SELECT * FROM exam_schedule ORDER BY date').fetchall()
    con.close()

    diff = list(set(new_data) - (set(old_data)))  # сравниваем данные
    if diff:
        for i in range(len(diff)):
            return_data += ' '.join(diff[i])
            return_data += '\n'
        if not old_data:
            return_data = f'Появилось расписание сессии:\n{return_data}'
            got_exams = True
        else:
            return_data = f'Произошли изменения в расписании экзаменов:\n{return_data}'
            got_exams = True
    return return_data, got_exams


def update_groups_params():
    """
    Обновляет group_ids.db в связи с появлением новых групп - загружает соответствующие им id на ИС "Расписание" ЛЭТИ
    :return: сообщение с оповещением для админской беседы, список групп для удаления, df пользователей для удаления
    """

    # Получаем данные
    url = 'https://digital.etu.ru/api/general/dicts/groups?scheduleId=publicated&withSemesterSeasons=true'
    data = requests.get(url, headers=headers).json()

    # Извлекаем и прописываем даты семестра
    dates = ["semesterStart", "semesterEnd", "examStart", "examEnd"]
    for el in range(len(data)):
        for d in dates:
            try:
                print(data[el]["semesterSeasons"][0]["GroupSemesterSeason"][d])
                data[el][d] = datetime.strptime(data[el]["semesterSeasons"][0]["GroupSemesterSeason"][d][:10], '%Y-%m-%d').date()
            except TypeError:  # значение даты None или неправильный путь (мб нет GroupSemesterSeason)
                data[el][d] = None

    # Преобразуем в датафрейм для удобства обработки
    df = pd.DataFrame(data)
    df = df[['id', 'fullNumber', 'course', 'semester', 'studyingType', 'educationLevel',
             "semesterStart", "semesterEnd", "examStart", "examEnd"]]

    # Помимо основных бэкапов, создаем простую копию БД group_ids, на случай необходимости быстрого восстановления
    os.system(f"cp {path}admindb/databases/group_ids.db {path}admindb/databases/group_ids_before_update.db")

    # Сравниваем с базой и обновляем при необходимости
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        old = pd.read_sql('SELECT etu_id, course, semester, studying_type, group_id FROM group_gcals', con)

        new_gs = set(df[['id', 'fullNumber']].itertuples(index=False, name=None))
        old_gs = set(old[['etu_id', 'group_id']].itertuples(index=False, name=None))
        to_add = new_gs - old_gs
        to_remove = old_gs - new_gs

        # Сперва обновляем (только, остальное все равно потом) etu_id у тех, кто НЕ в обеих группах (был и остается)
        staying = list(df.loc[~df.id.isin([el[0] for el in to_add]), ['id', 'fullNumber']].itertuples(index=False, name=None))
        cur.executemany("UPDATE group_gcals SET etu_id=? WHERE group_id=?", staying)
        con.commit()

        # Теперь разбираемся с изменениями
        # Старые группы (к удалению)
        remove_groups = [el[1] for el in to_remove]
        if to_remove:
            cur.execute(f"SELECT vk_chat_id, tg_chat_id, group_id FROM group_gcals "
                        f"WHERE group_id IN {tuple(remove_groups)}")
            groups_to_remove = pd.DataFrame(cur.fetchall(), columns=['vk_chat_id', 'tg_chat_id', 'group_id'])

            cur.execute(f"DELETE FROM group_gcals WHERE group_id IN {tuple(remove_groups)}")
            con.commit()

        # Собираем информацию о пользователях, у которых сбрасывается группа. Им нужно разослать уведомления
        cur.execute(f"SELECT group_id, vk_id, tg_id FROM user_ids "
                    f"WHERE group_id NOT IN (SELECT DISTINCT group_id FROM group_gcals)")
        users_to_remove = pd.DataFrame(cur.fetchall(), columns=['group_id', 'vk_id', 'tg_id'])

        cur.execute(f"DELETE FROM user_ids WHERE group_id NOT IN (SELECT DISTINCT group_id FROM group_gcals)")
        con.commit()

        # Новые группы
        if to_add:
            to_add = list(df.loc[df.index.isin([el[0] for el in to_add])].itertuples(index=False, name=None))
            cur.executemany("INSERT INTO group_gcals "
                            "(etu_id, group_id, course, semester, studying_type, level, "
                            "semester_start, semester_end, exam_start, exam_end) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", to_add)
            con.commit()

        # Обновляем все остальное. etu_id не трогаем - уже обновлено выше.
        df = list(df[['course', 'semester', 'studyingType', "semesterStart", "semesterEnd", "examStart", "examEnd",
                      "fullNumber"]].itertuples(index=False, name=None))
        cur.executemany("UPDATE group_gcals SET course=?, semester=?, studying_type=?, "
                        "semester_start=?, semester_end=?, exam_start=?, exam_end=? WHERE group_id=?", df)
        con.commit()
    con.close()

    # Удаляем файлы БД удаленных групп
    for group in groups_to_remove.group_id.to_list():
        try:
            os.remove(f"{path}/databases/{group}.db")
        except OSError:
            pass

    add_groups = [el[1] for el in to_add]
    message = f'Обновлена БД all_groups'
    if to_add:
        message += f'\nДобавлены группы ({len(add_groups)} шт.): {", ".join(add_groups)}'
    if to_remove:
        message += (f'\nУдалены группы ({groups_to_remove.shape[0]} шт.): '
                    f'{", ".join(groups_to_remove.group_id.to_list())}'
                    f'\nУдалено пользователей ({users_to_remove.shape[0]}):'
                    f'\n{users_to_remove.groupby("group_id").count()}')
    return message, groups_to_remove, users_to_remove
