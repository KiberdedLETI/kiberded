"""
Перезагрузка всяких кэшей и клавиатур
"""
import json
import math
import sys
import os
import re
import sqlite3
import pytz
import recurring_ical_events
from icalendar import Calendar
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import io
import random
from datetime import date, datetime, timedelta
import requests
import time
import requests
import vk_api
from vk_api.utils import get_random_id
from shiza.etu_parsing import parse_etu_ids, parse_exams, get_exam_data, parse_prepods_schedule, load_prepods_table_cache, load_table_cache
from shiza.databases_shiza_helper import edit_gcal, create_database, load_teacher_ids, get_stock_groups, \
    generate_subject_ids, generate_subject_keyboards, generate_subject_keyboards_tg, load_calendar_cache, \
    generate_main_keyboard, generate_links_keyboard, add_preset_books, generate_departments_keyboards
import keyboards_telegram.create_keyboards
from shiza.daily_functions import daily_cron
from bot_functions.bots_common_funcs import get_day, read_table

token = '806beaa2e069c4262f6b0d19ed8485c2c21857d2535aafb71f20c86876e8c1920997019e40782ee3318ad'  # обычный
group_id = 201485931
# group_id = 203476627  # админский
# token = '87b2fedaa8fd05516d417452d672b090bffc7d70b40ecb2e18588f8bcd82404cb5eb057daa8f76ada0af6'  # админский

days = [['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'], [' (чёт)', ' (нечёт)']]
tables = ['schedule', 'books', 'user_ids', 'prepods']
timetable = ['08:00', '09:50', '11:40', '13:40', '15:30', '17:20', '19:05', '20:50']
lesson_numbers_allowed = ['1', '2', '3', '4', '5', '6', '7', '8']
path = f'{os.path.abspath(os.curdir)}/'
today = date.today()
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'}


if __name__ == '__main__':
    generate_departments_keyboards()

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        con.row_factory = lambda cur, row: row[0]
        cur = con.cursor()
        stock_dbs = cur.execute('SELECT group_id FROM group_gcals').fetchall()
    con.close()

    for group in stock_dbs:
        print(group)
        generate_main_keyboard(group)  # создаем главную клавиатуру
        generate_links_keyboard(group)  # создаем клавиатуру с ссылками для тг
        generate_subject_ids(group)  # генерация таблицы subject_ids для тг
        generate_subject_keyboards(group)  # генерируем клавиатуры предметов и преподов для вк
        generate_subject_keyboards_tg(group)  # аналогично, для тг

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        con.row_factory = lambda cur, row: row[0]
        cur = con.cursor()
        stock_dbs = cur.execute('SELECT group_id FROM group_gcals WHERE isCustomDB=0').fetchall()
    con.close()

    print('books')
    for group in stock_dbs:
        print(group)
        _1, _2 = add_preset_books(group, True)

    load_table_cache()  # загружаем кэш расписаний
    load_calendar_cache()

    # load_table_cache()