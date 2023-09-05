# dependencies: []
"""
Перезагрузка всяких кэшей и клавиатур
"""
import os
import sqlite3
from shiza.etu_parsing import load_prepods_table_cache, load_table_cache
from shiza.databases_shiza_helper import generate_subject_ids, generate_subject_keyboards, \
    generate_subject_keyboards_tg, load_calendar_cache, generate_main_keyboard, generate_links_keyboard, \
    add_preset_books, generate_departments_keyboards, generate_prepods_keyboards

path = f'{os.path.abspath(os.curdir)}/'

if __name__ == '__main__':

    load_table_cache()  # загружаем кэш расписаний
    load_calendar_cache()

    generate_departments_keyboards()
    generate_prepods_keyboards()
    load_prepods_table_cache()

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        con.row_factory = lambda cur, row: row[0]
        cur = con.cursor()
        stock_dbs = cur.execute('SELECT group_id FROM group_gcals').fetchall()
    con.close()

    for group in stock_dbs:
        print(group)
        try:
            generate_main_keyboard(group)  # создаем главную клавиатуру
            generate_links_keyboard(group)  # создаем клавиатуру с ссылками для тг
            generate_subject_ids(group)  # генерация таблицы subject_ids для тг
            generate_subject_keyboards(group)  # генерируем клавиатуры предметов и преподов для вк
            generate_subject_keyboards_tg(group)  # аналогично, для тг
        except Exception as e:
            print(f'{group} - {e}')

    with sqlite3.connect(f'{path}admindb/databases/group_ids.db') as con:
        con.row_factory = lambda cur, row: row[0]
        cur = con.cursor()
        stock_dbs = cur.execute('SELECT group_id FROM group_gcals WHERE isCustomDB=0').fetchall()
    con.close()

    print('books')
    for group in stock_dbs:
        print(group)
        _1, _2 = add_preset_books(group, True)

