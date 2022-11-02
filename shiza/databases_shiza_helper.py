"""
Большой скрипт с кучей вспомогательных функций редактора БД
"""
import hashlib
import os
import time
import traceback
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards_telegram.create_keyboards import payload_to_callback
import sqlite3
import pandas as pd
import requests
from icalendar import Calendar
import pytz
from datetime import datetime, timedelta
from shiza.etu_parsing import parse_group_params, parse_exams, load_calendar_cache, load_table_cache
from datetime import date
import math
from transliterate import translit

days = [['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'], [' (чёт)', ' (нечёт)']]
lesson_numbers_allowed = ['1', '2', '3', '4', '5', '6', '7', '8']
parity_allowed = ['0', '1']
timetable = ['08:00', '09:50', '11:40', '13:40', '15:30', '17:20', '19:05', '20:50']
path = f'{os.path.abspath(os.curdir)}/'
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'}


def get_group(path, user_id) -> tuple:  # admindb группа (для freedom=admin/moderator)
    """
    Возвращает группу пользователя

    :param str path: путь к директории с БД
    :param user_id: id пользователя
    :return: (group,)
    """

    with sqlite3.connect(f'{path}admindb/databases/admins.db') as con:
        cursor = con.cursor()
        group = cursor.execute("SELECT group_id FROM users WHERE id=?", [user_id]).fetchone()
    con.close()
    return group  # Важно! Возвращает (group, ) todo а зачем так возвращает?


def get_common_group(path, user_id) -> str:  # группа из общего списка (для freedom=user)
    """
    Возвращает группу пользователя из общего списка

    :param str path: путь к директории с БД
    :param user_id: id пользователя
    :return: group
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cursor = con.cursor()
        cursor.execute("SELECT group_id FROM user_ids WHERE user_id=?", [user_id])
        group = cursor.fetchone()
    if group is not None:
        group = group[0]
    con.close()
    return group


def get_common_additional_group(path, user_id) -> str:  # доп. группа из общего списка (для freedom=user)
    """
    Возвращает доп. группу пользователя из общего списка

    :param str path: путь к директории с БД
    :param user_id: id пользователя
    :return: group
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cursor = con.cursor()
        cursor.execute("SELECT additional_group_id FROM user_ids WHERE user_id=?", [user_id])
        group = cursor.fetchone()
    if group is not None:
        group = group[0]
    con.close()
    return group


def get_stock_groups() -> list:
    """
    Возвращает список групп, у которых неотредактированные БД
    :return: [group_id1, ...]
    """
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        con.row_factory = lambda cur, row: row[0]
        cur = con.cursor()
        stock_dbs = cur.execute('SELECT group_id FROM group_gcals WHERE isCustomDB=0').fetchall()
    con.close()
    return stock_dbs


def watch_all_databases(path, group, freedom):
    """
    Просмотр всех доступных к редактированию БД в редакторе

    :param str path: путь к директории с БД
    :param str group: номер группы
    :param str freedom: уровень доступа
    :return: список в виде текста (для сообщения) и клавиатура-json
    """

    databases = os.listdir(path=f'{path}databases')
    answer = ''
    keyboard = VkKeyboard(one_time=False, inline=True)
    if freedom == 'admin' and 'admindb' in path:
        answer = 'Список баз:\n'
        for base in range(len(databases)):
            answer = answer + databases[base] + '\n'
            keyboard.add_button(label=databases[base], color=VkKeyboardColor.POSITIVE,
                                payload={"type": "shiza_action", "command": 'read_database',
                                         "database": f'{databases[base][:-3]}'})  # [:-3] это без ".db"
            if (base + 1) % 3 == 0:
                keyboard.add_line()
        if (base + 1) % 3 != 0:
            keyboard.add_line()

    elif f'{group}.db' in databases:
        answer = 'Данные твоей группы:'
        keyboard.add_button(label=f'{group}.db', color=VkKeyboardColor.POSITIVE,
                            payload={"type": "shiza_action", "command": 'read_database',
                                     "database": f'{group}'})
        keyboard.add_line()
        keyboard.add_button(label=f'Почта', color=VkKeyboardColor.POSITIVE,
                            payload={"type": "shiza_action", "command": f'view_email'})
        keyboard.add_button(label=f'Календарь', color=VkKeyboardColor.POSITIVE,
                            payload={"type": "shiza_action", "command": f'view_calendar'})
        keyboard.add_line()

    keyboard.add_button(label='В начало', color=VkKeyboardColor.PRIMARY, payload={"type": "shiza_navigation", "place": "start_databases"})
    keyboard.add_button(label='Конец работы', color=VkKeyboardColor.NEGATIVE, payload={"type": "shiza_navigation", "place": "end_databases"})
    return answer, keyboard.get_keyboard()


# см. выше, отличия - другие payload для дальнейшего вызова другой функции
def edit_all_databases(path, group, freedom):
    """
    Редактирование всех доступных к редактированию БД в редакторе

    :param str path: путь к директории с БД
    :param str group: номер группы
    :param str freedom: уровень доступа
    :return: список в виде текста (для сообщения) и клавиатура-json
    """

    databases = os.listdir(path=f'{path}databases')
    keyboard = VkKeyboard(one_time=False, inline=True)
    answer = 'Ошибка'
    if 'admindb' in path:
        answer = 'Список доступных для редактирования баз: \n'
        for base in range(len(databases)):
            answer += f'{databases[base]}\n'
        answer = 'Напиши базу из перечисленного списка.'
    elif freedom == 'admin' or freedom == 'moderator':
        answer = 'Тут ты можешь отредактировать базу данных группы. ' \
                 'При редактировании отключается автоматическое обновление (с сайта ЛЭТИ и учебников по умолчанию), ' \
                 'обновить вручную можно нажав на кнопку "Сброс БД" или "Добавить методички" (только раздел методичек).'
        keyboard.add_button(label=f'{group}.db', color=VkKeyboardColor.POSITIVE,
                            payload={"type": "shiza_action", "command": f'edit_database', "database": f'{group}'})
        keyboard.add_button(label=f'Сброс {group}.db', color=VkKeyboardColor.POSITIVE,
                            payload={"type": "shiza_action", "command": f'reset_database', "database": f'{group}'})
        keyboard.add_line()
        keyboard.add_button(label=f'Почта', color=VkKeyboardColor.POSITIVE,
                            payload={"type": "shiza_navigation", "place": f'view_email'})
        keyboard.add_button(label=f'Календарь', color=VkKeyboardColor.POSITIVE,
                            payload={"type": "shiza_navigation", "place": f'view_calendar'})
        keyboard.add_line()
        keyboard.add_button(label='Добавить методички',
                            payload={"type": "shiza_navigation", "place": "add_preset_books_info"},
                            color=VkKeyboardColor.POSITIVE)
        keyboard.add_line()

    keyboard.add_button(label='В начало', color=VkKeyboardColor.PRIMARY, payload={"type": "shiza_navigation", "place": "start_databases"})
    keyboard.add_button(label='Конец работы', color=VkKeyboardColor.NEGATIVE, payload={"type": "shiza_navigation", "place": "end_databases"})
    return answer, keyboard.get_keyboard()


def get_database_to_watch(database, path):  # чтобы не получать ту клавиатуру и тот ответ каждый раз
    """
    Получение клавиатуры и ответа для просмотра БД

    :param str database: выбранная БД
    :param str path: путь к директории с БД
    :return: 0, выгружает файл БД в формате .xlsx в директорию cache
    """

    with sqlite3.connect(f'{path}databases/{database}.db') as con:
        cursor = con.cursor()
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name!='table_cache'").fetchall()
        for table in range(len(tables)):
            sql_execute = f"SELECT * FROM {tables[table][0]}"
            df = pd.read_sql(sql_execute, con)
            try:
                with pd.ExcelWriter(f'{path}cache/{database}.xlsx', mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                    df.to_excel(writer, index=False, sheet_name=tables[table][0])
            except FileNotFoundError:
                with pd.ExcelWriter(f'{path}cache/{database}.xlsx', mode='w', engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name=tables[table][0])
    con.close()
    return 0


def load_teacher_ids(group):
    """
    Добавление teacher_id к таблице prepods
    :param str group: группа
    :return: 0
    """

    # Получение всех teacher_id
    with sqlite3.connect(f'{path}admindb/databases/prepods.db') as con:
        cur = con.cursor()
        fios = cur.execute('SELECT id, substring(surname || " " || name || " " || midname, 0) '
                           'FROM prepods').fetchall()
    con.close()
    fios = {fio[1]: fio[0] for fio in fios}

    add_column = f'ALTER TABLE prepods ADD COLUMN teacher_id integer'
    clear_col_query = f"UPDATE prepods SET teacher_id = NULL"
    get_prepods = f"SELECT name FROM prepods"
    insert_query = f"UPDATE prepods SET teacher_id = ? WHERE name = ?"

    # Добавление teacher_id в таблицу prepods базы group
    with sqlite3.connect(f'{path}databases/{group}.db') as con:
        cur = con.cursor()

        try:  # Пробуем добавить столбец teacher_id, потом можно убрать
            cur.execute(add_column)
            con.commit()
        except Exception:
            pass

        cur.execute(clear_col_query)
        con.commit()
        prepods = cur.execute(get_prepods).fetchall()

        prepods = [prepod[0] for prepod in prepods if prepod[0] in fios.keys()]
        ins_data = [(fios[prepod], prepod) for prepod in prepods]

        cur.executemany(insert_query, ins_data)
        con.commit()

    con.close()
    return 0


def create_database(group, is_global_parsing=False, keep_old_data_override=False, override_bool=False) -> str:
    """
    Создание БД для группы и все сопутствующие операции

    :param str group: номер группы
    :param bool is_global_parsing: if True, парсинг будет производиться в глобальном режиме - меньше уведомлений,
        все группы подряд (кроме кастомных)
    :param bool keep_old_data_override: if True, оставляет прошлые методы в БД, если они были (для допсы)
    :param bool override_bool: оверрайд для оверрайда keep_old_data_override...
    :return: сообщения с результатом парсинга для пользователя и для админов (в отладку)
    """

    if not keep_old_data_override:
        month_today = date.today().month  # чтобы посмотреть, оставлять ли методы
        keep_old_data = True if month_today in [2, 7, 8, 9] else False
    else:
        keep_old_data = override_bool

    with sqlite3.connect(f'{path}admindb/databases/all_groups.db') as con:  # достаем странный айдишник
        cur = con.cursor()
        etu_id = cur.execute("SELECT etu_id FROM all_groups WHERE fullNumber=?", [group]).fetchone()
        if etu_id:  # если группа такая существует
            etu_id = etu_id[0]
    con.close()

    try:  # парсер в расписон и преподов
        url = f'https://digital.etu.ru/api/schedule/ics-export/group?groups={etu_id}&scheduleId=publicated'
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
            return f'Отсутствует расписание {group}', f'Отсутствует расписание {group}'

        parity_count = []  # костыль для проверки четности, сравнение с первой неделей (первой парой) сема
        for component in full_cal.walk():
            if component.get('dtstart'):
                dtstart_par = component.get('dtstart').dt
                parity_count.append(dtstart_par)
        parity_count.sort()

        schedule_list = []
        prepods_list = []
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

        # Если БД уже есть, стираем и перезаписываем ее
        if f'{group}.db' in os.listdir(f'{path}databases/'):
            if keep_old_data:
                with sqlite3.connect(f'{path}databases/{group}.db') as con:
                    cur = con.cursor()
                    if not cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='books_old'").fetchall():
                        if cur.execute("SELECT * FROM books").fetchall():
                            generate_subject_keyboards(group, write_as_old=True)
                            cur.execute("ALTER TABLE books RENAME TO books_old")
                            cur.execute("ALTER TABLE prepods RENAME TO prepods_old")  # так и так есть
                        else:
                            keep_old_data = False  # тогда нечего ссылаться на пустую БД
                    elif f'{group}_subjects_old.json' not in os.listdir(f'{path}keyboards/'):
                        cur.execute("ALTER TABLE books RENAME TO books_temp")
                        cur.execute("ALTER TABLE prepods RENAME TO prepods_temp")
                        cur.execute("ALTER TABLE books_old RENAME TO books")
                        cur.execute("ALTER TABLE prepods_old RENAME TO prepods")
                        con.commit()
                        generate_subject_keyboards(group, write_as_old=True)
                        cur.execute("ALTER TABLE books RENAME TO books_old")
                        cur.execute("ALTER TABLE prepods RENAME TO prepods_old")
                        cur.execute("ALTER TABLE books_temp RENAME TO books")
                        cur.execute("ALTER TABLE prepods_temp RENAME TO prepods")  # что я творю...
                    con.commit()
                con.close()

            if not keep_old_data:
                os.remove(f'{path}databases/{group}.db')

        # перенос в SQL
        with sqlite3.connect(f'{path}databases/{group}.db') as con:
            cur = con.cursor()
            schedule.to_sql('schedule', con, if_exists='replace', index=False)
            prepods.to_sql('prepods', con, if_exists='replace', index=False)
            cur.execute('CREATE TABLE IF NOT EXISTS books(subject text, name text, doc_link text, file_link_tg text)')
            con.commit()
        con.close()

        # Догружаем id преподов для расписания преподов
        load_teacher_ids(group)

        # добавляем в group_ids если там еще не было, если есть - не трогаем
        with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
            cur = con.cursor()
            if not cur.execute("SELECT * FROM group_gcals WHERE group_id=?", [group]).fetchone():
                cur.execute("INSERT INTO group_gcals(group_id) VALUES(?)", [group])
            cur.execute('UPDATE group_gcals SET isCustomDB=0 WHERE group_id=?', [group])

        generate_main_keyboard(group)  # создаем главную клавиатуру
        generate_links_keyboard(group)  # создаем клавиатуру с ссылками для тг

        try:  # Обработка ошибки номера группы
            parse_group_params(group)  # парсим даты семестра
        except Exception as e:
            if is_global_parsing:
                pass
            else:
                raise e

        book_notif_user, book_notif_admin = add_preset_books(group, is_global_parsing)  # добавляем набор книжек
        generate_subject_ids(group)  # генерация таблицы subject_ids для тг
        generate_subject_keyboards(group)  # генерируем клавиатуры предметов и преподов для вк
        generate_subject_keyboards_tg(group)  # аналогично, для тг
        load_table_cache(group)  # загружаем кэш расписаний

        with con:
            if cur.execute('SELECT isExam FROM group_gcals WHERE group_id=?', [group]).fetchone()[0]:
                parse_exams(group)
        con.close()
    except Exception as e:
        if is_global_parsing:
            return '', f'\n{group} - Ошибка:{e}\n{traceback.format_exc()}\n'
        return f'Ошибка создания базы данных группы {group}. Обратись за помощью к администраторам.', \
               f'Ошибка создания БД: {e}\n{traceback.format_exc()}'
    if is_global_parsing:
        return '', f'{group} - Успешно\nМетоды:{book_notif_admin}\n'
    return f'База данных группы {group} успешно загружена!\n{book_notif_user}', book_notif_admin


def edit_database(database, path, url, group):
    # функция для обновления БД, загрузка по url через requests
    # можно редактировать: Методы, расписание, преподы.
    r = requests.get(url)
    with open(f"{path}cache/{database}.xlsx", "wb") as code:
        code.write(r.content)
    if os.path.exists(f'{path}cache/{database}.db'):  # если уже есть база в cache - удаляем
        os.remove(f'{path}cache/{database}.db')

    with sqlite3.connect(f'{path}cache/{database}.db') as con:
        dfs = pd.read_excel(f'{path}cache/{database}.xlsx', sheet_name=None, keep_default_na=False,
                            dtype=str, engine='openpyxl')  # todo sheet exam_sxhedule, check if exists and raise errors
        for table, df in dfs.items():
            df[df.columns] = df.apply(lambda x: x.str.strip())  # чистим пробелы в данных
            df.to_sql(table, con, if_exists='replace', index=False)
        # проверки на правильность данных
        days_check = str(set(dfs['schedule']['weekday'].unique()) - set(days[0]))
        lesson_numbers_check = str(set(dfs['schedule']['lesson_number'].unique()) - set(lesson_numbers_allowed))
        parity_check = str(set(dfs['schedule']['parity'].unique()) - set(parity_allowed))
        books_check = str(set(dfs['books']['subject'].unique()) - set(dfs['schedule']['subject'].unique()))
        # мб books_check стоит сравнивать с преподами тоже
        if days_check != 'set()':
            raise ValueError(f'Ошибка в днях недели расписания: {days_check}')
        if lesson_numbers_check != 'set()':
            raise ValueError(f'Ошибка в номерах пар: {lesson_numbers_check}')
        if parity_check != 'set()':
            raise ValueError(f'Ошибка в параметре четности: {parity_check}')
        if books_check != 'set()':
            raise ValueError(f'Ошибка в предметах методичек: {books_check}')
    con.close()
    
    os.replace(f"{path}cache/{database}.db", f"{path}databases/{database}.db")
    generate_subject_keyboards(group)  # редачим клавиатуры с предметами для преподов и метод
    os.remove(f"{path}cache/{database}.xlsx")

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        cur.execute('UPDATE group_gcals SET isCustomDB=1 WHERE group_id=?', [group])
    con.close()

    load_table_cache(group)  # загружаем кэш расписаний
    return 0


def edit_admin_database(database, path, url):  # для админских БД
    """
    Обновление админских БД с полной перезаписью данных.

    :param str database: название загружаемой БД
    :param str path: путь к директории с БД
    :param str url: url с файлом из сообщения (ссылка на сервер ВК)
    :return:
    """

    r = requests.get(url)
    with open(f"{path}cache/{database}.xlsx", "wb") as code:
        code.write(r.content)
    if os.path.exists(f'{path}cache/{database}.db'):  # если уже есть база в cache - удаляем
        os.remove(f'{path}cache/{database}.db')
    with sqlite3.connect(f'{path}cache/{database}.db') as con:
        dfs = pd.read_excel(f'{path}cache/{database}.xlsx', sheet_name=None, keep_default_na=False, dtype=str,
                            engine='openpyxl')
        for table, df in dfs.items():
            df.to_sql(table, con, if_exists='replace', index=False)
    con.close()
    os.replace(f"{path}cache/{database}.db", f"{path}databases/{database}.db")
    os.remove(f"{path}cache/{database}.xlsx")
    return 0


# Просмотр календаря и почты
def view_email(group):
    """
    Просмотр почты из БД в диалоге

    :param group: номер группы
    :return: сообщение с информацией о почте
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        mail_data = cur.execute('SELECT mail, mail_password '
                                'FROM group_gcals '
                                'WHERE group_id=? AND chat_id IS NOT NULL', [group]).fetchall()
        unauthorized_td_chats = cur.execute('SELECT tg_chat_id '
                                            'FROM group_gcals '
                                            'WHERE group_id=? AND chat_id IS NULL', [group]).fetchall()

    con.close()
    mail_data = list(mail_data[0])
    if mail_data[0]:  # если есть почта группы
        ans = f'Почта: подключена\nАдрес: {mail_data[0]}\nПароль: {mail_data[1]}'
        if unauthorized_td_chats:
            ans += f' Была обнаружена беседа в Телеграме, не привязанная к ВК, туда уведомления отправляться ' \
                   f'не будут. Синхронизация бесед пока недоступна, можно только создать новую в Телеграме. ' \
                   f'Команда в беседе ВК [club201485931|@kiberded_bot] телеграм'
            #   Чтобы привязать беседу, напиши в беседе ВК "@kiberded_bot телеграм"'
    else:
        ans = 'Почта: не подключена'
    return ans


def view_gcal(group):
    """
    Просмотр календаря из БД в диалоге

    :param group: номер группы
    :return: сообщение с информацией о календаре
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        mail_cal_data = cur.execute('SELECT gcal_link '
                                    'FROM group_gcals '
                                    'WHERE group_id=? AND chat_id IS NOT NULL', [group]).fetchone()[0]
        unauthorized_td_chats = cur.execute('SELECT tg_chat_id '
                                            'FROM group_gcals '
                                            'WHERE group_id=? AND chat_id IS NULL', [group]).fetchall()

    con.close()
    if mail_cal_data:  # если есть почта группы
        load_calendar_cache(group)  # Обновляем кэш календаря, на всякий
        ans = f'Календарь: подключен\nКэш календаря обновлен\nСсылка: {mail_cal_data}'
        if unauthorized_td_chats:
            ans += f' Была обнаружена беседа в Телеграме, не привязанная к ВК, туда календарь отправляться не будет. ' \
                   f'Синхронизация бесед пока недоступна, можно только создать новую в Телеграме. ' \
                   f'Команда в беседе ВК [club201485931|@kiberded_bot] телеграм'
            # ans += f'Была обнаружена беседа в Телеграме, не привязанная к ВК, туда календарь отправляться не будет.\n' \
            #        f'Чтобы привязать беседу, напиши в беседе ВК "@kiberded_bot телеграм"'
    else:
        ans = 'Календарь: не подключен.'
    return ans


# Изменение параметров группы (номер для юзера, модеры, почта)
def edit_email(group, email='', password=''):  # добавление почты (проверки на правильность в шизе)
    """
    Изменение почты группы

    :param str group: номер группы
    :param str email: почта
    :param str password: пароль
    :return: 0
    """
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        # Вот здесь в запросе нужно будет убрать AND chat_id IS NOT NULL если отдельно для ТГ делать.
        # Это проверка на неавторизованные беседы
        old_data = cur.execute(f"SELECT mail, mail_password, mail_imap group_gcals "
                               f"FROM group_gcals "
                               f"WHERE group_id={group} "
                               f"AND chat_id IS NOT NULL").fetchall()

        if old_data:
            old_data = old_data[0]
            # Сравниваем данные со старыми, если передаются пустые аргументы - оставляем старые данные
            email = email if email else old_data[0]
            mail_imap = email.split('@')[-1] if email else ''
            imap_address = f'imap.{mail_imap}' if email else old_data[2]
            password = password if password else old_data[1]
        else:
            email = email
            mail_imap = email.split('@')[-1]
            imap_address = f'imap.{mail_imap}'
            password = password
        
        cur.execute(f"UPDATE group_gcals SET mail=?, mail_password=?, mail_imap=? "
                    f"WHERE group_id={group} "
                    f"AND chat_id IS NOT NULL",
                    [email, password, imap_address])
        con.commit()
    con.close()
    generate_main_keyboard(group)
    return 0


def edit_gcal(group, gcal=''):  # добавление календаря (проверки на правильность в шизе)
    """
    Изменение календаря группы

    :param str group: номер группы
    :param str gcal: ссылка на календарь
    :return: сообщение с информацией о загруженном календаре
    """

    if gcal:
        if not gcal.startswith('https://calendar.google.com/calendar/ical/'):
            return 'Неверная ссылка на календарь. Сейчас поддерживаются только goole-календари.'

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        # Вот здесь в запросе нужно будет убрать AND chat_id IS NOT NULL если отдельно для ТГ делать.
        # Это проверка на неавторизованные беседы
        old_gcal = cur.execute(f"SELECT gcal_link group_gcals "
                               f"FROM group_gcals "
                               f"WHERE group_id={group} "
                               f"AND chat_id IS NOT NULL").fetchone()
        if old_gcal:
            old_gcal = old_gcal[0]
            if not gcal:
                gcal = old_gcal
        
        cur.execute(f"UPDATE group_gcals "
                    f"SET gcal_link=? "
                    f"WHERE group_id=? "
                    f"AND chat_id IS NOT NULL", (gcal, group))
    con.close()

    generate_main_keyboard(group)  # Обновляем клавиатуру
    load_calendar_cache(group)  # Обновляем кэш календаря
    return f'Данные календаря успешно загружены, главная клавиатура обновлена.'


def delete_email(group):
    """
    Удаление почты группы
    :param str group: номер группы
    :return: 0
    """
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        cur.execute('UPDATE group_gcals SET mail=null, mail_password=null, mail_imap=null WHERE group_id=?', [group])
    con.close()
    generate_main_keyboard(group)
    generate_links_keyboard(group)
    return 0


def delete_gcal(group):
    """
    Удаление календаря группы
    :param group: номер группы
    :return: 0
    """
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        cur.execute('UPDATE group_gcals SET gcal_link=null WHERE group_id=?', [group])
    con.close()

    # Удаляем кэш календаря
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
        cur.execute('DELETE FROM calendar_cache WHERE group_id=?', [group])
        con.commit()

    generate_main_keyboard(group)
    return 0


def remove_old_data(group) -> bool:
    """
    Удаление старых методичек из БД группы
    :param str group: номер группы
    :return: True, если было что-то в старых методах, иначе False - от этого зависит наличие уведомления
    """

    with sqlite3.connect(f'{path}databases/{group}.db') as con:
        cur = con.cursor()
        try:
            return_status = True if cur.execute("SELECT * FROM books_old").fetchall() else False  # сообщать ли об этом
        except sqlite3.OperationalError:
            return_status = False
        cur.execute("DROP TABLE IF EXISTS prepods_old")
        cur.execute("DROP TABLE IF EXISTS books_old")
        con.commit()
    con.close()
    generate_subject_keyboards(group)
    return return_status


def add_moderator(user_id, group_num):
    """
    Добавление модератора в группу
    :param user_id: id пользователя, которого добавляем в группу
    :param str group_num: номер группы
    :return: сообщение с информацией о добавлении модератора
    """

    return_message = ''
    con = sqlite3.connect(f'{path}admindb/databases/admins.db')
    cur = con.cursor()
    if not cur.execute('''SELECT * FROM users WHERE id=?''', [user_id]).fetchall():
        cur.execute('''INSERT INTO users (id, group_id) VALUES (?, ?)''', [user_id, group_num])

    cur.execute('''UPDATE users SET freedom = 'moderator' WHERE id=?''', [user_id])
    con.commit()
    con.close()
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        if not cur.execute('''SELECT * FROM user_ids WHERE user_id=?''', [user_id]).fetchall():
            cur.execute('''INSERT INTO user_ids (user_id, group_id) VALUES (?, ?)''', [user_id, group_num])
        else:  # передвигаем юзера в нужную группу если что
            cur.execute('''UPDATE user_ids SET group_id=? WHERE user_id=?''', (user_id, group_num))
        return_message += f'Пользователь @id{user_id} добавлен в модераторы'
    con.close()

    # добавляем в общие айди
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        if not cur.execute('''SELECT * FROM user_ids WHERE user_id=?''', [user_id]).fetchall():
            cur.execute('''INSERT INTO user_ids (user_id, group_id) VALUES (?, ?)''', [user_id, group_num])
    return return_message


def check_group_exists(group_num):
    """
    Проверка наличия группы в БД по all_groups и директории с БД

    :param str group_num: номер группы
    :return: True, если группа есть, иначе False
    """

    if f"{group_num}.db" not in os.listdir(f'{path}databases/'):
        return False

    with sqlite3.connect(f'{path}admindb/databases/all_groups.db') as con:
        cur = con.cursor()
        return True if cur.execute('''SELECT fullNumber FROM all_groups WHERE fullNumber=?''', [group_num]).fetchone() else False


# шиза для юзеров
def change_user_group(group_id, user_id, source='vk'):  # меняет группу юзера и смотрит, есть ли БД этой группы
    """
    Изменение группы юзера

    :param group_id: номер группы
    :param user_id: id пользователя
    :param str source: источник изменения группы ('vk' или 'tg')
    :return: bool существует ли БД для данной группы; bool был ли юзер в боте; сообщение об изменении группы
    """

    id_col = 'user_id' if source == 'vk' else 'telegram_id'

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        if cur.execute(f'SELECT * FROM user_ids WHERE {id_col}=?', [user_id]).fetchone():  # если уже был
            cur.execute(f'UPDATE user_ids SET group_id=? WHERE {id_col}=?', (group_id, user_id))
            user_existed = True
        else:  # если юзер только присоединился
            cur.execute(f'INSERT INTO user_ids ({id_col}, group_id) VALUES (?, ?)', (user_id, group_id))
            user_existed = False
    con.close()

    with sqlite3.connect(f'{path}admindb/databases/admins.db') as con:  # если есть модер новой группы, то есть и её БД.
        cur = con.cursor()
        if not cur.execute('''SELECT * FROM users WHERE group_id=?''', [group_id]).fetchall():
            if f'{group_id}.db' not in os.listdir(f'{path}databases/'):
                group_exists = False
            else:
                group_exists = True

            # todo message for tg
            answer = f'Номер группы {group_id} установлен. \nВ этой группе еще нет модератора, поэтому функционал' \
                     f' бота несколько ограничен - нельзя редактировать данные и добавить гугл-календарь и почту ' \
                     f'группы. \nОбратись к администраторам, мы назначим кого-нибудь модератором. \nВзаимодействуй' \
                     f' с ботом кнопками на всплывающей клавиатуре. Если клавиатура не появилась, напиши что-нибудь.'
        else:
            answer = f'Группа успешно изменена на {group_id}'
            group_exists = True
    return group_exists, user_existed, answer


def change_user_additional_group(group_id, user_id, source='vk'):  # меняет группу юзера и смотрит, есть ли БД этой группы
    """
    Изменение дополнительной группы юзера
    TODO: поддержка дополнительной группы в телеграме

    :param group_id: номер группы
    :param user_id: id пользователя
    :param str source: источник изменения группы ('vk' или 'tg')
    :return: bool существует ли БД для данной группы; bool был ли юзер в боте; сообщение о добавлении группы
    """

    id_col = 'user_id' if source == 'vk' else 'telegram_id'
    if group_id != '0000':
        with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
            cur = con.cursor()
            cur.execute(f'UPDATE user_ids SET additional_group_id=? WHERE {id_col}=?', (group_id, user_id))
            user_existed = True
        con.close()
        answer = f'Дополнительная группа успешно изменена на {group_id}'
        group_exists = True
        return group_exists, user_existed, answer
    else:
        with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
            cur = con.cursor()
            cur.execute(f'UPDATE user_ids SET additional_group_id=NULL WHERE {id_col}=?', [user_id])
            user_existed = True
        con.close()
        answer = f'Дополнительная группа успешно удалена.'
        group_exists = True
        return group_exists, user_existed, answer


# генерация таблицы с предметами и их id для тг
def generate_subject_ids(group):
    """
    Генерация таблицы с предметами и их id для тг
    :param group: номер группы
    :return: 0 если все ок
    """
    with sqlite3.connect(f'{path}databases/{group}.db') as con:
        cur = con.cursor()
        cur.execute(f'DROP TABLE IF EXISTS subject_ids')
        cur.execute(f'CREATE TABLE subject_ids (subject TEXT, id TEXT)')
        cur.execute(f'SELECT DISTINCT subject FROM prepods')
        subjects = cur.fetchall()
        for subject in subjects:
            cur.execute(f'INSERT INTO subject_ids (subject, id) VALUES (?, ?)',
                        (subject[0], hashlib.md5(subject[0].encode('utf-8')).hexdigest()[:20]))
        con.commit()
    con.close()
    return subjects


# Создание главной, предметной и links клавиатур группы - используется в create/edit_database
def generate_subject_keyboards(group, write_as_old=False):  # создает клавиатуры с предметами
    """
    Создает клавиатуры с предметами для бота ВК

    :param str group: номер группы
    :param bool write_as_old: if True, записывает предметы в БД как предыдущие
    :return: 0
    """

    with sqlite3.connect(f'{path}/databases/{group}.db') as con:
        cur = con.cursor()

        link_to_old = False
        if cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='books_old'").fetchall() and not write_as_old:
            link_to_old = True

        old_or_new = '_old' if write_as_old else ''

        cur.execute('SELECT DISTINCT subject from prepods')  # достаем список предметов группы
        subject_list = cur.fetchall()
        # создание клавиатуры "предметы"
        count = len(subject_list)  # счетчик для новой строки
        new_subjects = VkKeyboard(one_time=False)
        for subject_number in range(len(subject_list)):
            if cur.execute('SELECT * FROM books WHERE subject=?', [subject_list[subject_number][0]]).fetchall():
                button_color = VkKeyboardColor.POSITIVE
            else:
                button_color = VkKeyboardColor.SECONDARY

            new_subjects.add_button(str(*subject_list[subject_number]), color=button_color,
                                    payload={"type": "action",
                                             "action_type": "message",
                                             "command": f"get_books{old_or_new}",
                                             "subject": str(*subject_list[subject_number])})
            count += -1
            if count % 3 == 0 and count != 0:  # по 3 элемента в строке максимум
                new_subjects.add_line()

    new_subjects.add_line()

    if link_to_old:
        new_subjects.add_button('Предыдущий семестр',
                                payload={"type": "navigation",
                                         "place": "books_old"})
        new_subjects.add_line()
    elif write_as_old:
        new_subjects.add_button('Текущий семестр',
                                payload={"type": "navigation",
                                         "place": "books"})
        new_subjects.add_line()

    new_subjects.add_button('Вернуться в начало',
                            payload={"type": "navigation",
                                     "place": "main"})
    with open(f'{path}keyboards/{group}_subjects{old_or_new}.json', 'w', encoding='utf-8') as f:  # записываем в соотв. JSON
        f.write(new_subjects.get_keyboard())

    # создание клавиатуры "преподы"
    count = len(subject_list)  # счетчик для новой строки
    new_prepods = VkKeyboard(one_time=False)  # генерируем клавиатуру для преподов группы
    for subject_number in range(len(subject_list)):
        new_prepods.add_button(str(*subject_list[subject_number]), color=VkKeyboardColor.POSITIVE,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": f"get_prepods{old_or_new}",
                                        "subject": str(*subject_list[subject_number])})
        count += -1
        if count % 3 == 0 and count != 0:  # по 3 элемента в строке максимум
            new_prepods.add_line()
    new_prepods.add_line()

    if link_to_old:
        new_prepods.add_button('Предыдущий семестр',
                           payload={"type": "navigation",
                                    "place": "prepods_old"})
        new_prepods.add_line()
    elif write_as_old:
        new_subjects.add_button('Текущий семестр',
                                payload={"type": "navigation",
                                         "place": "prepods"})
        new_subjects.add_line()

    new_prepods.add_button('Вернуться в начало',
                           payload={"type": "navigation",
                                    "place": "main"})
    with open(f'{path}keyboards/{group}_prepods{old_or_new}.json', 'w', encoding='utf-8') as f:  # записываем в соотв. JSON
        f.write(new_prepods.get_keyboard())

    if not link_to_old and not write_as_old:
        try:
            os.remove(f'{path}keyboards/{group}_subjects_old.json')
            os.remove(f'{path}keyboards/{group}_prepods_old.json')
        except OSError:
            pass
    return 0


def generate_subject_keyboards_tg(group):  # создает клавиатуры с предметами для телеграма
    """
    Создает клавиатуры с предметами для телеграма

    :param group: номер группы
    :return: 0 если все ок, ValueError в случае длинного предмета (ограничение на 64 символа, доступно 26)
    """
    with sqlite3.connect(f'{path}/databases/{group}.db') as con:
        cur = con.cursor()

        cur.execute('SELECT * from subject_ids')  # достаем список предметов группы
        subject_list = cur.fetchall()
        # создание клавиатуры "предметы"
        new_subjects = InlineKeyboardMarkup()
        new_subjects.row_width = 3

        # Тимур, прости за костыли, иначе я не придумал. И потомки тоже простите. Да, я верю в то, что потомки будут

        for subject_number in range(len(subject_list) // 3):  # тут отличие от создания для вк, т.к. нет метода add_line

            first_subject = subject_list[subject_number * 3]
            second_subject = subject_list[subject_number * 3 + 1]
            third_subject = subject_list[subject_number * 3 + 2]

            first_payload = {"type": "action",
                             "action_type": "message",
                             "command": f"get_books",
                             "subject": first_subject[1]}
            second_payload = {"type": "action",
                              "action_type": "message",
                              "command": f"get_books",
                              "subject": second_subject[1]}
            third_payload = {"type": "action",
                             "action_type": "message",
                             "command": f"get_books",
                             "subject": third_subject[1]}

            first_callback = payload_to_callback(first_payload)
            second_callback = payload_to_callback(second_payload)
            third_callback = payload_to_callback(third_payload)

            if len(first_callback) > 64:
                raise ValueError(f'Слишком длинный callback: {first_callback}, длина {len(first_callback)}')
            if len(second_callback) > 64:
                raise ValueError(f'Слишком длинный callback: {second_callback}, длина {len(second_callback)}')
            if len(third_callback) > 64:
                raise ValueError(f'Слишком длинный callback: {third_callback}, длина {len(third_callback)}')

            new_subjects.add(InlineKeyboardButton(first_subject[0], callback_data=first_callback),
                             InlineKeyboardButton(second_subject[0], callback_data=second_callback),
                             InlineKeyboardButton(third_subject[0], callback_data=third_callback))

        if len(subject_list) % 3 == 2:  # если остаток от деления на 3 = 2, то надо еще две кнопки снизу закинуть
            first_subject = subject_list[-2]
            second_subject = subject_list[-1]

            first_payload = {"type": "action",
                             "action_type": "message",
                             "command": f"get_books",
                             "subject": first_subject[1]}
            second_payload = {"type": "action",
                              "action_type": "message",
                              "command": f"get_books",
                              "subject": second_subject[1]}

            first_callback = payload_to_callback(first_payload)
            second_callback = payload_to_callback(second_payload)

            if len(first_callback) > 64:
                raise ValueError(f'Слишком длинный callback: {first_callback}, длина {len(first_callback)}')
            if len(second_callback) > 64:
                raise ValueError(f'Слишком длинный callback: {second_callback}, длина {len(second_callback)}')

            new_subjects.add(InlineKeyboardButton(first_subject[0], callback_data=first_callback),
                             InlineKeyboardButton(second_subject[0], callback_data=second_callback))
        elif len(subject_list) % 3 == 1:  # аналогично, последнюю кнопку
            first_subject = subject_list[-1]

            first_payload = {"type": "action",
                             "action_type": "message",
                             "command": f"get_books",
                             "subject": first_subject[1]}

            first_callback = payload_to_callback(first_payload)

            if len(first_callback) > 64:
                raise ValueError(f'Слишком длинный callback: {first_callback}, длина {len(first_callback)}')

            new_subjects.add(InlineKeyboardButton(first_subject[0], callback_data=first_callback))

        with open(f'{path}keyboards_telegram/{group}_books.json', 'w',
                  encoding='utf-8') as f:  # записываем в соотв. JSON
            f.write(new_subjects.to_json())

        # создание клавиатуры "предметы"
        new_prepods = InlineKeyboardMarkup()
        new_prepods.row_width = 3

        for subject_number in range(
                len(subject_list) // 3):  # тут отличие от создания для вк, т.к. нет метода add_line

            first_subject = subject_list[subject_number * 3]
            second_subject = subject_list[subject_number * 3 + 1]
            third_subject = subject_list[subject_number * 3 + 2]

            first_payload = {"type": "action",
                             "action_type": "message",
                             "command": f"get_prepods",
                             "subject": first_subject[1]}
            second_payload = {"type": "action",
                              "action_type": "message",
                              "command": f"get_prepods",
                              "subject": second_subject[1]}
            third_payload = {"type": "action",
                             "action_type": "message",
                             "command": f"get_prepods",
                             "subject": third_subject[1]}

            first_callback = payload_to_callback(first_payload)
            second_callback = payload_to_callback(second_payload)
            third_callback = payload_to_callback(third_payload)

            if len(first_callback) > 64:
                raise ValueError(f'Слишком длинный callback: {first_callback}, длина {len(first_callback)}')
            if len(second_callback) > 64:
                raise ValueError(f'Слишком длинный callback: {second_callback}, длина {len(second_callback)}')
            if len(third_callback) > 64:
                raise ValueError(f'Слишком длинный callback: {third_callback}, длина {len(third_callback)}')

            new_prepods.add(InlineKeyboardButton(first_subject[0], callback_data=first_callback),
                             InlineKeyboardButton(second_subject[0], callback_data=second_callback),
                             InlineKeyboardButton(third_subject[0], callback_data=third_callback))

        if len(subject_list) % 3 == 2:  # если остаток от деления на 3 = 2, то надо еще две кнопки снизу закинуть
            first_subject = subject_list[-2]
            second_subject = subject_list[-1]

            first_payload = {"type": "action",
                             "action_type": "message",
                             "command": f"get_prepods",
                             "subject": first_subject[1]}
            second_payload = {"type": "action",
                              "action_type": "message",
                              "command": f"get_prepods",
                              "subject": second_subject[1]}

            first_callback = payload_to_callback(first_payload)
            second_callback = payload_to_callback(second_payload)

            if len(first_callback) > 64:
                raise ValueError(f'Слишком длинный callback: {first_callback}, длина {len(first_callback)}')
            if len(second_callback) > 64:
                raise ValueError(f'Слишком длинный callback: {second_callback}, длина {len(second_callback)}')

            new_prepods.add(InlineKeyboardButton(first_subject[0], callback_data=first_callback),
                             InlineKeyboardButton(second_subject[0], callback_data=second_callback))
        elif len(subject_list) % 3 == 1:  # аналогично, последнюю кнопку
            first_subject = subject_list[-1]

            first_payload = {"type": "action",
                             "action_type": "message",
                             "command": f"get_prepods",
                             "subject": first_subject[1]}

            first_callback = payload_to_callback(first_payload)
            if len(first_callback) > 64:
                raise ValueError(f'Слишком длинный callback: {first_callback}, длина {len(first_callback)}')

            new_prepods.add(InlineKeyboardButton(first_subject[0], callback_data=first_callback))

    payload = {"type": "navigation",
               "place": "table_prepods"}
    callback_data = payload_to_callback(payload)
    btn_back = InlineKeyboardButton('Расписание преподавателей', callback_data=callback_data)
    new_prepods.add(btn_back)

    with open(f'{path}keyboards_telegram/{group}_prepods.json', 'w',
              encoding='utf-8') as f:  # записываем в соотв. JSON
        f.write(new_prepods.to_json())
    return 0


def generate_main_keyboard(group):  # создает главную клавиатуру на основании group_ids.db
    """
    Создает клавиатуры для ВК и ТГ для главного меню с разным набором кнопок в зависимости от наличия
    почты/календаря в базе

    :param group: номер группы
    :return: 0
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        main_kb_data = cur.execute("SELECT gcal_link, mail FROM group_gcals WHERE group_id=?", [group]).fetchall()[0]
    con.close()
    mail = ''
    kb_template = 'keyboard_main'  # важно! сперва добавляется _mail, потом _cal (так устроены названия шаблонов)
    kb_template_mail = ''
    kb_template_cal = ''
    if main_kb_data[1]:
        mail = main_kb_data[1].split(sep='@')[-1]
        kb_template_mail = '_mail'
    if main_kb_data[0]:  # добавляем кнопку календаря если он есть
        kb_template_cal = '_cal'
    with open(f'{path}keyboards/{kb_template}{kb_template_mail}{kb_template_cal}.json', 'r', encoding='utf-8') as f:
        main_temp = f.read()
    with open(f'{path}keyboards/{group}_main.json', 'w', encoding='utf-8') as f:
        if mail:
            f.write(main_temp.replace("mail_url_placeholder", f'https://{mail}'))
        else:
            f.write(main_temp)
    with open(f'{path}keyboards_telegram/{kb_template}{kb_template_cal}.json', 'r', encoding='utf-8') as f:
        main_temp_telegram = f.read()
    with open(f'{path}keyboards_telegram/{group}_main.json', 'w', encoding='utf-8') as f:
        f.write(main_temp_telegram)
    return 0


def generate_links_keyboard(group):  # создает клавиатуру с ссылками для ТГ todo: кастомизация из базы
    """
    Создает клавиатуру со ссылками для ТГ в зависимости от наличия почты

    :param group: номер группы
    :return: 0
    """
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        main_kb_data = cur.execute("SELECT mail FROM group_gcals WHERE group_id=?", [group]).fetchall()[0]
    con.close()
    mail = ''
    kb_template = 'keyboard_links'
    kb_template_mail = ''
    if main_kb_data[0]:
        mail = main_kb_data[0].split(sep='@')[-1]
        kb_template_mail = '_mail'
    with open(f'{path}keyboards_telegram/{kb_template}{kb_template_mail}.json', 'r', encoding='utf-8') as f:
        main_temp_telegram = f.read()
    with open(f'{path}keyboards_telegram/{group}_links.json', 'w', encoding='utf-8') as f:
        if mail:
            f.write(main_temp_telegram.replace("mail_url_placeholder", f'https://{mail}'))
        else:
            f.write(main_temp_telegram)
    return 0


def create_departments_db():
    """
    Создаёт базу данных с названиями кафедр и их id
    :return: 0
    """

    url = 'https://digital.etu.ru/api/general/dicts/departments'
    r = requests.get(url, headers=headers).json()
    # returns rows {"id":45,"title":"Баз.каф.АИ","type":"normal","facultyId":3}

    with sqlite3.connect(f'{path}admindb/databases/prepods.db') as con:
        cur = con.cursor()
        cur.execute('DROP TABLE IF EXISTS departments')
        cur.execute(
            'CREATE TABLE IF NOT EXISTS departments (id INTEGER PRIMARY KEY, title TEXT, type TEXT, facultyId INTEGER)')
        for row in r:
            print(row)
            if not row['facultyId']:
                row['facultyId'] = 0
            cur.execute(
                f'INSERT INTO departments VALUES ({row["id"]}, "{row["title"]}", "{row["type"]}", {row["facultyId"]})')
        con.commit()
    con.close()

    return 0


def generate_departments_keyboards():  # создает клавиатуры для ТГ с кафедрами для поиска препода
    """
    Создает набор клавиатур (на момент октября 2022 года - это 60 кафедр -> 2 клавиатуры 8*3+1*3 + еще одна).
    Внизу есть кнопки навигации между клавиатурами (вперед-назад)
    Создает файлы keyboard_departments_0.json, ...1.json, ...
    :return: 0 если все ок
    """
    with sqlite3.connect(f'{path}admindb/databases/prepods.db') as con:
        cur = con.cursor()
        departments = cur.execute("SELECT * FROM departments ORDER BY title").fetchall()
    con.close()
    buttons = []  # лист с кнопками для будущего удобства

    for department in departments:
        # формирование callback-ов:
        payload = {"type": "action",
                   "action_type": "message",
                   "command": f"choose_department",
                   "id": str(department[0])}
        callback = payload_to_callback(payload)

        # отсечение "каф." в начале названия кафедры
        if department[1].startswith('каф.'):
            department_name = department[1][4:]
        # отчечение "Баз.каф." в начале названия кафедры
        elif department[1].startswith('Баз.каф.'):
            department_name = department[1][8:]
        else:
            department_name = department[1]
        buttons.append(InlineKeyboardButton(department_name, callback_data=callback))

    for i in range(math.ceil(len(departments) / 24)):  # делим на 24 кнопки в каждой клавиатуре
        markup = InlineKeyboardMarkup()
        markup.row_width = 3
        for j in range(8):  # 8 строк в каждой клавиатуре
            if i * 24 + j * 3 + 2 < len(departments):  # чтобы не выйти за пределы списка
                markup.add(buttons[i * 24 + j * 3 + 0], buttons[i * 24 + j * 3 + 1], buttons[i * 24 + j * 3 + 2])
            elif i * 24 + j * 3 + 1 < len(departments):  # если осталось всего 2 кнопки:
                markup.add(buttons[i * 24 + j * 3 + 0], buttons[i * 24 + j * 3 + 1])
            elif i * 24 + j * 3 < len(departments):  # если осталась одна кнопка:
                markup.add(buttons[i * 24 + j * 3 + 0])
        if i == 0:  # если это первая клавиатура, то нужно добавить только кнопку вперед
            payload = {"type": "action",
                       "action_type": "message",
                       "command": f"search_department",
                       "list_id": str(i + 1)
                       }
            callback_next = payload_to_callback(payload)
            markup.add(InlineKeyboardButton('>', callback_data=callback_next))
        elif i == ((math.ceil(len(departments) / 24)) - 1):  # если последняя, то нужно добавить только кнопку назад
            payload = {"type": "action",
                       "action_type": "message",
                       "command": f"search_department",
                       "list_id": str(i - 1)
                       }
            callback_prev = payload_to_callback(payload)
            markup.add(InlineKeyboardButton('<', callback_data=callback_prev))
        else:  # если не первая и не последняя, то нужно добавить обе кнопки
            payload = {"type": "action",
                       "action_type": "message",
                       "command": f"search_department",
                       "list_id": str(i + 1)
                       }
            callback_next = payload_to_callback(payload)
            payload = {"type": "action",
                       "action_type": "message",
                       "command": f"search_department",
                       "list_id": str(i - 1)
                       }
            callback_prev = payload_to_callback(payload)
            markup.add(InlineKeyboardButton('<', callback_data=callback_prev),
                       InlineKeyboardButton('>', callback_data=callback_next))
        payload = {"type": "navigation",
                   "place": "table_prepods"}
        callback_data = payload_to_callback(payload)
        btn_back = InlineKeyboardButton('Назад', callback_data=callback_data)
        markup.add(btn_back)
        with open(f'{path}keyboards_telegram/keyboard_departments_{i}.json', 'w',
                  encoding='utf-8') as f:  # записываем в соотв. JSON
            f.write(markup.to_json())
    return 0


def generate_prepods_keyboards():  # создает клавиатуры для ТГ с преподами для поиска препода
    """
    Создает набор клавиатур (на момент октября 2022 года - это 60 кафедр -> минимум 60 клавиатур).
    Внизу есть кнопки навигации между клавиатурами (вперед-назад), если преподов больше 8
    Создает файлы keyboard_prepods_{id}_{num}.json, где id - номер кафедры, num - порядковый номер с нуля, если больше 8
    :return: 0 если все ок
    """
    # получение списка кафедр
    with sqlite3.connect(f'{path}admindb/databases/prepods.db') as con:
        cur = con.cursor()
        departments = cur.execute("SELECT * FROM departments ORDER BY id").fetchall()
    con.close()
    for department in departments:
        id = department[0]
        # получение списка преподов:
        with sqlite3.connect(f'{path}admindb/databases/prepods.db') as con:
            cur = con.cursor()
            prepods = cur.execute(f"SELECT * FROM prepods WHERE department_id = {id} ORDER BY surname").fetchall()
        con.close()
        buttons = []
        # формирование кнопок, чтоб потом удобнее было:
        for prepod in prepods:
            payload = {"type": "action",
                       "action_type": "message",
                       "command": f"choose_prepod",
                       "id": str(prepod[0]),
                       "department_id": str(id)
                       }
            callback = payload_to_callback(payload)
            buttons.append(InlineKeyboardButton(f'{prepod[2]}', callback_data=callback))
        # формирование клавиатур:
        is_many_keyboards = True if len(prepods) > 8 else False
        for i in range(math.ceil(len(buttons) / 8)):  # количество клавиатур
            markup = InlineKeyboardMarkup()
            for j in range(8):  # количество кнопок в клавиатуре
                if i * 8 + j < len(buttons):  # если кнопка существует
                    markup.add(buttons[i * 8 + j])
            if i == 0 and is_many_keyboards:  # если это первая клавиатура, то нужно добавить только кнопку вперед
                payload = {"type": "action",
                           "action_type": "message",
                           "command": f"search_prepod",
                           "list_id": str(i + 1),
                           "department_id": str(id)
                           }
                callback_next = payload_to_callback(payload)
                markup.add(InlineKeyboardButton('>', callback_data=callback_next))
            elif i == (math.ceil(len(buttons) / 8) - 1) and is_many_keyboards:  # если последняя, то нужно добавить только кнопку назад
                payload = {"type": "action",
                           "action_type": "message",
                           "command": f"search_prepod",
                           "list_id": str(i - 1),
                           "department_id": str(id)
                           }
                callback_prev = payload_to_callback(payload)
                markup.add(InlineKeyboardButton('<', callback_data=callback_prev))
            elif is_many_keyboards:
                payload = {"type": "action",
                           "action_type": "message",
                           "command": f"search_prepod",
                           "list_id": str(i - 1),
                           "department_id": str(id)
                           }
                callback_prev = payload_to_callback(payload)
                payload = {"type": "action",
                           "action_type": "message",
                           "command": f"search_prepod",
                           "list_id": str(i + 1),
                           "department_id": str(id)
                           }
                callback_next = payload_to_callback(payload)
                markup.add(InlineKeyboardButton('<', callback_data=callback_prev),
                           InlineKeyboardButton('>', callback_data=callback_next))
            payload = {"type": "action",
                       "action_type": "message",
                       "command": f"search_department",
                       "list_id": str(0)
                       }
            callback_next = payload_to_callback(payload)
            markup.add(InlineKeyboardButton('Назад к выбору кафедры', callback_data=callback_next))
            with open(f'{path}keyboards_telegram/keyboard_prepods_{id}_{i}.json', 'w',
                      encoding='utf-8') as f:  # записываем в соотв. JSON
                f.write(markup.to_json())
        if len(buttons) == 0:  # на случай отсутствия преподов, например как в военке
            markup = InlineKeyboardMarkup()
            payload = {"type": "action",
                       "action_type": "message",
                       "command": f"search_department",
                       "list_id": str(0)
                       }
            callback_next = payload_to_callback(payload)
            markup.add(InlineKeyboardButton('Назад к выбору кафедры', callback_data=callback_next))
            with open(f'{path}keyboards_telegram/keyboard_prepods_{id}_{0}.json', 'w',
                      encoding='utf-8') as f:  # записываем в соотв. JSON
                f.write(markup.to_json())
    return 0


def add_preset_books(group, is_global_parsing=False) -> str:  # добавление пресетов метод
    """
    Добавляет пресеты книг в базу данных
    Структура файлов: название - 2_2 - факультет(как в группе)_семестр.
    В файле листы groups - группы с пресетами для каждой.

    :param str group: номер группы
    :param bool is_global_parsing: if True, парсинг пресетов будет в глобальном режиме - меньше логи
    :return: сообщения о статусе загрузки для пользователя и в отладку
    """

    user_str = ''
    admin_str = ''
    with sqlite3.connect(f'{path}admindb/databases/all_groups.db') as con:
        cur = con.cursor()
        try:
            semester = str(cur.execute('SELECT semester FROM all_groups WHERE fullNumber=?', [group]).fetchone()[0])
        except TypeError:
            return f'Группа {group} не найдена', f'Группа {group} не найдена'
    con.close()

    faculty = group[1]  # факультет - вторая цифра
    sheet_code = group[2:]  # направление
    filename = f'{faculty}_{semester}'

    with sqlite3.connect(f'{path}databases/{group}.db') as con:
        con.row_factory = lambda cursor, row: row[0]  # чтобы возвращать list, а не list of tuples
        cur = con.cursor()
        subject_list = cur.execute('SELECT DISTINCT subject FROM schedule').fetchall()
    try:
        df = pd.read_excel(f'{path}databases/books/{filename}.xlsx', sheet_name=sheet_code,
                           keep_default_na=False, dtype=str, engine='openpyxl')
        books = df.loc[df['subject'].isin(subject_list)]  # отметаем то, что не подходит по названию предмета, на всякий

        if len(df.index) > len(books.index):  # если что-то отмелось, заметим это
            user_str = f'\nВ процессе создания БД методичек не записалось {len(df.index) - len(books.index)} файлов.' \
                       f'Добавлено {len(books.index)} файлов.' \
                       f'Скорее всего, не совпали названия предметов в файле с книжками по умолчанию и у вас в группе.' \
                       f'\nЕсли посчитаешь, что чего-то капитально не хватает, обратись к администраторам, мы поможем' \
                       f' решить проблему. \nПопытаться заново создать список методичек по умолчанию можно в: ' \
                       f'Настройки - Работа с БД - Добавить методички'
            admin_str = f'\nДефолтные методички для {group} частично не загрузились - не записалось' \
                        f' {len(df.index) - len(books.index)} файлов. \nЗаписалось {len(books.index)} файлов'
            if is_global_parsing:
                admin_str = f'Частично - {len(books.index)}/{len(df.index)}'

        books[books.columns] = books.apply(lambda x: x.str.strip())  # чистим пробелы в данных
        with con:  # заносим в SQL БД
            books.to_sql(con=con, name='books', if_exists='replace', index=False)
        con.close()
        user_str = f'В раздел "Методички" загружены учебники по умолчанию. {user_str}'
        if is_global_parsing and not admin_str:
            admin_str = 'Успешно.'
        else:
            admin_str = f'В {group} успешно загружены методички по умолчанию {admin_str}'

    except FileNotFoundError:  # если нет файла с методами
        user_str = f'Списка учебников по умолчанию не найдено. Раздел "Методички" создан пустым, ' \
                   'добавлять туда файлы может модератор группы, см. статью на странице сообщества.'
        if is_global_parsing:
            admin_str = f'Отсутствуют - нет {filename}.xlsx'
        else:
            admin_str = f'Нету методичек для {group}, cеместр {semester}'
    except ValueError as e:  # нету листа в файле
        user_str = f'Списка учебников по умолчанию не найдено. Раздел "Методички" создан пустым, ' \
                   'добавлять туда файлы может модератор группы, см. статью на странице сообщества.'
        if is_global_parsing:
            admin_str = f'Отсутствуют - нет "{sheet_code}" в {filename}.xlsx'
        else:
            admin_str = f'Нету листа методичек в {filename}.xlsx для {group}, cеместр {semester}\n{e}'
    except Exception as e:  # пока оставлю на другие ошибки
        user_str = f'Списка учебников по умолчанию не найдено. Раздел "Методички" создан пустым, ' \
                     'добавлять туда файлы может модератор группы, см. статью на странице сообщества.'
        admin_str = f'Неизвестная ошибка добавления методичек для {group}, cеместр {semester}: ' \
                    f'{e}\n{traceback.format_exc()}'
    return user_str, admin_str