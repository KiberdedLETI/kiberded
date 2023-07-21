# dependencies: [chat_bot, telegram_bot, scheduler]
"""
Составление сообщений из icalendar / обычного расписания пользователю/в беседу
"""
import re
import time
import pytz
import requests
from datetime import date, datetime, timedelta
import sqlite3
import sys
import os
import toml
from hashlib import sha256

# init
try:
    config = toml.load('configuration.toml')
except FileNotFoundError:
    # todo logging?
    sys.exit()

path = config.get('Kiberded').get('path')
group_token = config.get('Kiberded').get('group_token')
group_id = 0
token = config.get('Kiberded').get('token')
days = [['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'], [' (чёт)', ' (нечёт)']]
timetable = config.get('Kiberded').get('timetable')
lesson_length = config.get('Kiberded').get('lesson_length')
tables_time = config.get('Kiberded').get('tables_time')
dk_day = config.get('Kiberded').get('dk_day')  # todo летний/зимний ДК
today = datetime.now(pytz.timezone('Europe/Moscow')).date()
#  \init


def read_calendar(group, date='today') -> str:
    """
    Чтение календаря из кэша или с сервера

    :param str group: номер группы
    :param str date: 'today' или 'tomorrow'
    :return: содержимое календаря в формате icalendar
    """

    with sqlite3.connect(f'{path}cache/calendar_cache.db') as con:
        cur = con.cursor()
        cal = cur.execute(f"SELECT {date} FROM calendar_cache WHERE group_id='{group}'").fetchone()
    if cal:
        return cal[0]
    return None


def get_day(now_date=today):  #
    """
    :param now_date: дата в datetime.date
    :return: дата в формате 'День + (чет/нечет)'
    """

    weeknumfix = 1  # Поправочка на случай несовпадения четности с календарной
    weekday = days[0][now_date.weekday()]
    parity = days[1][((weeknumfix + now_date.isocalendar()[1]) % 2)]
    return weekday + parity


def read_table(group, day=get_day(today)) -> str:
    """
        Чтение расписания из кэша или с сервера

        :param str group: номер группы
        :param str day: Понедельник (чёт) и т.д.
        :return: содержимое расписания в формате icalendar
    """

    with sqlite3.connect(f'{path}databases/{group}.db') as con:
        cur = con.cursor()
        table = cur.execute(f"SELECT day_table FROM table_cache WHERE day='{day}'").fetchone()[0]
    con.close()
    return table


def day_of_day_toggle(group) -> str:  #
    """
    Вкл/Выкл отправку картинок в беседу. Находится здесь, потому что юзается в chat_bot и cron

    :param group: номер группы
    :return: сообщение с оповещением о включении/выключении
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        day_of_day_old = cur.execute("SELECT with_dayofday FROM group_gcals WHERE group_id=?", [group]).fetchone()[0]
        day_of_day_new = not day_of_day_old
        cur.execute('UPDATE group_gcals SET with_dayofday=? WHERE group_id=?', (int(day_of_day_new), group))
    con.close()

    if day_of_day_new:
        return 'Функция подключена. Теперь с ежедневным расписанием будут присылаться всякие пикчи типа ' \
               '"С днем цемента!" (как это появилось в боте вообще, лучше не спрашивать...). ' \
               'Пикчи не наши, если что, и там всякое может быть. \nВыключить можно повторным нажатием.'
    else:
        return 'Функция отключена. Подключить можно повторным нажатием'


def weekly_toast_toggle(group):  # переключает присылание тостов в конфу. Здесь, потому что юзается в chat_bot и cron
    """
    Вкл/Выкл отправку тостов по окончании пар на неделе в беседу. Находится здесь, потому что юзается в chat_bot и cron

    :param group: номер группы
    :return: сообщение с оповещением о включении/выключении
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        toast_old = cur.execute("SELECT with_toast FROM group_gcals WHERE group_id=?", [group]).fetchone()[0]
        toast_new = not toast_old
        cur.execute('UPDATE group_gcals SET with_toast=? WHERE group_id=?', (int(toast_new), group))
    con.close()

    if toast_new:
        return 'Функция подключена. Теперь после каждой последней пары на неделе Дед будет присылать рандомный ' \
               'тост \nЖеня допиши сюда что-нибудь смешное'
    else:
        return 'Функция отключена. Подключить можно повторным нажатием'


def get_last_lesson(group, day=get_day(datetime.now().date())):
    """
    Достает время конца последней пары на неделе

    :param group: номер группы
    :param day: день, по умолчанию дата сегодня
    :return: bool
    """
    parity = '1' if day.split()[-1] == 'нечёт' else '0'
    with sqlite3.connect(f'{path}databases/{group}.db') as con:
        cur = con.cursor()
        for i in range(len(days[0])):
            last_daily_lesson = cur.execute("SELECT * FROM schedule WHERE weekday=? AND parity=? ORDER BY {} ASC".format('lesson_number'), (days[0][i], parity)).fetchall()
            if not last_daily_lesson:
                last_day = days[0][i - 1]
                if last_day == day.split()[0]:
                    last_daily_lesson = cur.execute("SELECT * FROM schedule WHERE weekday=? AND parity=? ORDER BY {} ASC".format('lesson_number'), (last_day, parity)).fetchall()[-1][2]
                    lesson_end = (datetime.strptime(timetable[int(last_daily_lesson) - 1], '%H:%M')+timedelta(minutes=95)).time()
                    return True, lesson_end
                break
    con.close()
    return False, 0


def get_exams(group) -> str:
    """
    Достает в одно сообщение все экзамены группы из таблицы с ними (при наличии оной)

    :param group: номер группы
    :return: сообщение с расписанием экзаменов
    """

    with sqlite3.connect(f'{path}databases/{group}.db') as con:
        today = datetime.today().date()
        cur = con.cursor()
        str_to_vk = ''
        if not cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exam_schedule'").fetchone():
            return 'Ошибка: расписания экзаменов не найдено.'
        else:
            for row in cur.execute('SELECT * FROM exam_schedule ORDER BY date'):
                exam_date = datetime.strptime(row[0], '%Y-%m-%d').date()
                days_left = (exam_date - today).days
                if days_left < 0:
                    continue

                if len(row) > 5:
                    if row[5] != '':  # дата консультации
                        consult_date = datetime.strptime(row[5], '%Y-%m-%d').date()
                        c_days_left = (consult_date - today).days

                        if c_days_left >= 0:
                            str_to_vk += f'{row[5][8:10]}.{row[5][5:7]} {row[6]} - {row[2]}, Консультация'

                            if row[7] != '':
                                str_to_vk += f' - {row[7]}'
                            str_to_vk += f'\n'

                str_to_vk += f'{row[0][8:10]}.{row[0][5:7]} {row[1]} - {row[2]}'  # День.Месяц Время - Предмет
                if row[3] != '':  # ФИО
                    str_to_vk += f', {row[3]}'
                if row[4] != '':  # Аудитория
                    str_to_vk += f' - {row[4]}'

                str_to_vk += f'\nДо экзамена осталось дней: {days_left}'
                str_to_vk += '\n\n'
    con.close()

    # Также добавляем инфу про день качества (дата = exam_end), если дата имеется
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        dk_date = cur.execute('SELECT exam_end FROM group_gcals WHERE group_id=?', [group]).fetchone()
        if dk_date:
            dk_date = datetime.strptime(dk_date[0], '%Y-%m-%d').date()
            days_left = (dk_date - today).days
            dk_date = f'{dk_date.day}.0{dk_date.month}'  # 0 потому что или 01 или 06...

    if not str_to_vk:  # Если экзамены закончились, присылаем инфу о ДК, чтобы не отправлять пустое сообщение
        if dk_date:
            str_to_vk = f'Экзамены закончились.\n{dk_date} - День качества'
            str_to_vk += f'\nОсталось дней: {days_left}'
        else:
            str_to_vk = f'Экзамены закончились, остался день качества'
    elif dk_date:  # К обычному расписанию тоже добавляем про ДК
        str_to_vk += f'{dk_date} - День качества'
        str_to_vk += f'\nОсталось дней: {days_left}'
    return str_to_vk


def get_exam_notification(group, day=date.today()) -> str:
    """
    Сообщение с экзаменом/консультацией на заданный день из таблицы exam_schedule (при наличии)

    :param str group: группа
    :param date day: день. По умолчанию - сегодня и завтра
    :return: сообщение с расписанием
    """

    # По умолчанию смотрим сегодня-завтра
    exam_days = [day] if day != date.today() else [date.today(), date.today() + timedelta(days=1)]
    exam_msg = ''

    with sqlite3.connect(f'{path}databases/{group}.db') as con:
        cur = con.cursor()
        if cur.execute("SELECT name FROM sqlite_master "  # если нет таблицы с экзаменами, то ничего не присылаем
                       "WHERE type='table' AND name='exam_schedule'").fetchone() is not None:

            for exam_day in exam_days:
                exam = cur.execute('SELECT time, subject, name, classroom '
                                   'FROM exam_schedule WHERE date=?', [exam_day]).fetchone()

                if exam is not None:  # Экзамен
                    exam_msg = f'в {exam[0]} экзамен по {exam[1]}' \
                               f'\nПреподаватель - {exam[2]}' \
                               f'\nАудитория {exam[3]}' \
                               f'\nУдачи!'

                else:  # Консультация
                    consult = cur.execute('SELECT subject, name, consult_date, consult_time, consult_classroom '
                                          'FROM exam_schedule '
                                          'WHERE consult_date=?', [exam_day]).fetchone()
                    if consult is not None:
                        exam_msg = f'в {consult[3]} консультация по {consult[0]}' \
                                   f'\nПреподаватель - {consult[1]}'
                        if consult[4] != '':
                            exam_msg += f'\nАудитория {consult[4]}'

                if exam_msg:
                    if day == date.today():
                        exam_msg = f"Сегодня {exam_msg}\n"
                    elif day == date.today() + timedelta(days=1):
                        exam_msg = f"Завтра {exam_msg}"
                    else:
                        exam_msg = f"{exam_day} {exam_msg}"
    return exam_msg


def get_prepods(subject, group_id, is_old=False) -> str:
    """
    Получение данных о преподавателях заданного предмета

    :param str subject: предмет
    :param group_id: номер группы
    :param bool is_old: if True, смотрит предмет предыдущего семестра
    :return: сообщение с преподавателями по данному предмету
    """

    str_to_vk = 'Преподы:\n'
    if is_old:
        query = f"SELECT name,subject_type FROM prepods_old WHERE subject=?"
    else:
        query = f"SELECT name,subject_type FROM prepods WHERE subject=?"

    with sqlite3.connect(f'{path}databases/{group_id}.db') as con:
        cursor = con.cursor()
        try:
            for row in cursor.execute(query, [subject]):
                str_to_vk += f'{row[0]} - {row[1]}\n'
        except Exception as e:
            str_to_vk += 'Возникла какая-то ошибка'
    return str_to_vk


def get_subjects(group) -> list:
    """
    Получение всех предметов группы

    :param group: номер группы
    :return: [subject1, subject2, ...]
    """

    with sqlite3.connect(f'{path}databases/{group}.db') as con:
        cur = con.cursor()
        subjects = []
        for row in cur.execute('SELECT DISTINCT subject from prepods'):
            subjects += row
    return subjects


def get_donators():
    """
    Статистика по группам-донатерам
    """
    ans = 'Список донатеров:'
    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        for row in cur.execute('SELECT group_id, with_dayofday, with_toast FROM group_gcals WHERE is_donator=TRUE'):
            ans += f'\n{row[0]}:\n' \
                   f'- Пикчи {"подключены" if row[1] else "отключены"}\n' \
                   f'- Тост {"подключен" if row[2] else "отключен"}\n'
    con.close()
    return ans


def group_is_donator(group) -> bool:
    """
    Смотрит донатный статус группы

    :param group: номер группы
    :return: (bool isDonate; дата окончания if isDonate=True else 0)
    """

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        if cur.execute("SELECT is_donator FROM group_gcals WHERE group_id=?", [group]).fetchone()[0]:  # bool 0/1
            return True
    return False


def get_tables_settings(user_id, source='tg'):
    """
    Получение настроек рассылки расписаний для пользователя
    """

    with sqlite3.connect(f'{path}admindb/databases/table_ids.db') as con:
        cur = con.cursor()
        upd_query = f'SELECT time, type, format FROM `{source}_users` WHERE id=?'
        cur.execute(upd_query, (user_id,))

        if cur.rowcount == 0:
            return f'Ты не подписан(-а) на рассылку расписаний.\nНастройки рассылки расписаний:'

        else:
            time_, type_, format_ = cur.fetchone()  # format пока не используется
            if time_ is None:
                time_ = tables_time
            if type_ is None:
                type_ = 'ежедневный и еженедельный'
            else:
                mode_names = {'calendar': 'календарь',
                              'daily': 'ежедневный',
                              'weekly': 'еженедельный',
                              'both': 'ежедневный и еженедельный'}
                type_ = mode_names[type_]

            ret_str = f'Текущие настройки рассылки:\n' \
                      f'Время: {time_}\n' \
                      f'Режим: {type_}\n'
            return ret_str


def add_user_to_table(user_id, count, source='vk') -> str:  # добавление user_id в table_ids для рассылки расписонов
    """
    Добавление пользователя в рассылку расписания

    :param user_id: id пользователя
    :param str count: '1'/'-1' (некрасивые параметры, да) - добавить/удалить пользователя соответственно
    :param str source: 'vk' / 'tg' - источник сообщения
    :return: сообщение о подписке/отписке/ошибке
    """

    str_to_vk = 'Ты не подписывался(-ась) на расписания'
    with sqlite3.connect(f'{path}admindb/databases/table_ids.db') as con:
        cursor = con.cursor()
        cursor.execute(f" CREATE TABLE IF NOT EXISTS {source}_users(id text, count text) ")
        data = cursor.execute(f"SELECT count FROM {source}_users WHERE id =?", [user_id]).fetchone()

        if data is None and count == '1':
            cursor.execute(f'INSERT INTO {source}_users (id, count) VALUES({user_id}, {count})')
            str_to_vk = f'Подписка на рассылку оформлена! ' \
                        f'Теперь тебе каждый день в {tables_time} МСК будет приходить расписание в личные сообщения.' \
                        f'\nНастроить рассылку ты можешь кнопками ниже:'

        elif data is not None:
            if count == '-1':
                cursor.execute(f"DELETE FROM {source}_users WHERE id=?", [user_id])
                str_to_vk = f'Подписка на рассылку расписаний отменена.'
            else:
                str_to_vk = f'Подписка на рассылку расписаний включена.\n{get_tables_settings(user_id, source)}'

    con.close()
    return str_to_vk


def set_table_mode(user_id, mode, source='tg'):
    """
    Настройка подписки на расписания (режим рассылки)
    """

    with sqlite3.connect(f'{path}admindb/databases/table_ids.db') as con:
        cur = con.cursor()
        upd_query = f'UPDATE `{source}_users` SET type=? WHERE id=?'
        cur.execute(upd_query, (mode, user_id))
        con.commit()

    mode_names = {'calendar': 'календарь',
                  'daily': 'ежедневный',
                  'weekly': 'еженедельный',
                  'both': 'ежедневный и еженедельный'}
    msg = f'Режим рассылки изменен на {mode_names[mode]}. Изменения вступят в силу со следующего дня'
    return msg


def add_user_to_anekdot(user_id, count, source='vk') -> str:
    """
    Добавление пользователя в базу для рассылки анекдотов

    :param user_id: id пользователя
    :param str count: '1'/'-1' - инкремент к счетчику подписки пользователя
    :param str source: 'vk' / 'tg' - источник сообщения
    :return: сообщение о статусе подписки
    """

    str_to_vk = 'Ты не подписывался(-ась) на анекдоты'

    with sqlite3.connect(f'{path}admindb/databases/anekdot_ids.db') as con:
        cursor = con.cursor()
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {source}_users(id text, count text)")
        data = cursor.execute(f"SELECT count FROM {source}_users WHERE id =?", [user_id]).fetchone()

        if data is None and count == '1':
            cursor.execute(f'INSERT INTO {source}_users (id, count) VALUES({user_id}, {count})')
            str_to_vk = f'Подписка на рассылку (очень посредственных) анекдотов оформлена! ' \
                        f'Теперь тебе каждый день в 7:00 МСК будет приходить {count} анекдот(а/ов)' \
                        f'\nP.S. Анекдоты не наши, это с https://www.anekdot.ru'

        elif data is not None and int(data[0]) + int(count) >= 0:
            cursor.execute(f'UPDATE {source}_users SET count = {str(int(count)+int(data[0][0]))} WHERE id = {user_id}')
            anek_count = cursor.execute(f"SELECT count FROM {source}_users WHERE id =?", [user_id]).fetchone()
            if anek_count[0] == '0':
                cursor.execute(f"DELETE FROM {source}_users WHERE id=?", [user_id])
                str_to_vk = f'Подписка на рассылку анекдотов отменена.'
            else:
                str_to_vk = f'Подписка на рассылку анекдотов обновлена. ' \
                            f'Теперь тебе каждый день в 7:00 МСК будет приходить {anek_count[0]} анекдот(а/ов)'
    con.close()

    return str_to_vk


def create_link_to_telegram(user_id, hash_key="", source=""):
    """
    Создает ссылку для авторизации пользователя в боте в телеграме. Ссылка содержит id пользователя и токен

    :param hash_key: Дополнительный ключ для создания токена ИЗ КОНФИГА
    :param user_id: id пользователя ВКонтакте
    :param str source: Источник перехода: "" - пользователь, "group" - беседа
    :return: link, user_id, token
    """

    user_id = str(user_id)
    user_str = bytearray(f"KDed{user_id[::-1]}{hash_key}", 'utf-8')
    m = sha256(user_str).hexdigest()[:48]  # В ТГ ограничение 64 символа, а нам нужно еще user_id передать
    tg_link = f"https://telegram.me/kiberded_leti_bot?start{source}={user_id}_{m}"
    return tg_link, user_id, m


def compile_group_stats(peer_id, admin_stats=False, source='vk') -> str:  # Здесь, потому что используется в обоих ботах
    """
    Сборка статистики группы: количество участников, статус группы, почта, календарь

    :param int peer_id: id беседы
    :param bool admin_stats: if True, собирает данные всего бота, а не по одной группе
    :param str source: источник данных (vk/tg), по умолчанию vk
    :return: сообщение со статистикой группы/бота
    """

    id_col = 'vk_chat_id' if source == 'vk' else 'tg_chat_id'

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        cur = con.cursor()
        all_stats = cur.execute(f'SELECT gcal_link, mail, is_donator, with_dayofday, group_id, with_toast '
                                f'FROM group_gcals WHERE {id_col}=?', [peer_id]).fetchall()

        all_users = cur.execute('SELECT group_id FROM user_ids '
                                'WHERE group_id=?', [all_stats[0][4]]).fetchall()
        all_g_users_vk = cur.execute('SELECT group_id FROM user_ids '
                                     'WHERE group_id=? AND user_id IS NOT NULL', [all_stats[0][4]]).fetchall()
        all_g_users_tg = cur.execute('SELECT group_id FROM user_ids '
                                     'WHERE group_id=? AND telegram_id IS NOT NULL', [all_stats[0][4]]).fetchall()

    ans = f'Статистика группы {all_stats[0][4]}:\n'
    if all_stats:
        all_stats = list(all_stats[0])
        all_stats[0] = 'Подключен' if all_stats[0] else 'Не подключен'  # календарь
        all_stats[1] = 'Не подключена' if not all_stats[1] else 'Подключена'  # почта
        ans += f'Пользователей - {len(all_users)}\n' \
               f'-- из ВКонтакте: {len(all_g_users_vk)}\n' \
               f'-- из Telegram: {len(all_g_users_tg)}\n' \
               f'Календарь: {all_stats[0]}\n' \
               f'Почта: {all_stats[1]}\n' \
               f'id беседы: {peer_id}\n'
        if all_stats[2]:  # донатики
            ans += f'Донатные функции - подключены до {all_stats[2]}\n' \
                   f'Доступные функции:\n' \
                   f'Ежедневная пикча - {"включена" if all_stats[3] else "отключена"}\n' \
                   f'Еженедельный тост - {"включен" if all_stats[5] else "отключен"}'
    else:
        ans += 'Ошибка: не удалось собрать данные о группе'

    if admin_stats:
        with con:
            all_users_total = cur.execute('SELECT group_id FROM user_ids').fetchall()
            all_users_vk = cur.execute('SELECT group_id FROM user_ids WHERE user_id IS NOT NULL').fetchall()
            all_users_tg = cur.execute('SELECT group_id FROM user_ids WHERE telegram_id IS NOT NULL').fetchall()
            all_groups = cur.execute('SELECT DISTINCT group_id FROM user_ids').fetchall()
            all_chats = cur.execute('SELECT group_id FROM group_gcals WHERE vk_chat_id IS NOT NULL').fetchall()
            all_tg_chats = cur.execute('SELECT group_id FROM group_gcals WHERE tg_chat_id IS NOT NULL').fetchall()
            all_mail = cur.execute('SELECT group_id FROM group_gcals WHERE mail IS NOT NULL').fetchall()
            all_gcals = cur.execute('SELECT group_id FROM group_gcals WHERE gcal_link IS NOT NULL').fetchall()
            all_donators = cur.execute('SELECT group_id FROM group_gcals WHERE is_donator IS NOT NULL').fetchall()
            ans += '\n\nГлобальная статистика:\n' \
                   f'Всего пользователей {len(all_users_total)}:\n' \
                   f'-- из ВКонтакте: {len(all_users_vk)}\n' \
                   f'-- из Telegram: {len(all_users_tg)}\n' \
                   f'Всего групп: {len(all_groups)-1}\n' \
                   f'Бесед подключено: {len(all_chats)}\n' \
                   f'-- в т.ч. в Telegram: {len(all_tg_chats)}\n' \
                   f'Почт подключено: {len(all_mail)}\n' \
                   f'Календарей подключено: {len(all_gcals)}\n' \
                   f'Донатеров: {len(all_donators)}'  # -1 в всего групп т.к. две 9281
        con.close()

        with sqlite3.connect(f'{path}admindb/databases/anekdot_ids.db') as con:
            con.row_factory = lambda cur, row: row[0]
            cur = con.cursor()
            vk_anekdot_ids = cur.execute('SELECT count FROM vk_users').fetchall()
            tg_anekdot_ids = cur.execute('SELECT count FROM tg_users').fetchall()
            vk_total = sum([int(count) for count in vk_anekdot_ids])
            tg_total = sum([int(count) for count in tg_anekdot_ids])
            ans += f'\nШутников ВК: {len(vk_anekdot_ids)}' \
                   f'\nШутников ТГ: {len(tg_anekdot_ids)}' \
                   f'\nВсего анекдотов отправляется: ' \
                   f'ВК - {vk_total}; ' \
                   f'ТГ - {tg_total}; ' \
                   f'Итого - {vk_total + tg_total}'
        con.close()

        with sqlite3.connect(f'{path}admindb/databases/table_ids.db') as con:
            con.row_factory = lambda cur, row: row[0]
            cur = con.cursor()
            vk_table_ids = cur.execute('SELECT count FROM vk_users').fetchall()
            tg_table_ids = cur.execute('SELECT count FROM tg_users').fetchall()
            vk_total = sum([int(count) for count in vk_table_ids])
            tg_total = sum([int(count) for count in tg_table_ids])
            ans += f'\nРасписаний ВК: {len(vk_table_ids)}' \
                   f'\nРасписаний ТГ: {len(tg_table_ids)}' \
                   f'\nВсего расписаний: {vk_total + tg_total}'
        con.close()

    return ans
