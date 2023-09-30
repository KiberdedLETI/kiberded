# dependencies: [telegram_bot]
"""
Здесь находится код для генерации всех клавиатур для телеграма, общих для пользователей бота

При запуске файла генерятся json-файлы в папку keyboards_telegram

По сути, повторяет логику клавиатур из вк. Отличия:
- Все ссылки находятся в отдельной группе, объединенной в "Полезные ссылки"
  (т.к. в телеге нельзя добавить кнопку с url в non-inline клавиатуре, да и мне кажется мало кому это надо)
- В начальных кнопках нет payload-а (он же callback_data), есть только в inline
  (опять же спс telegram api)
- Из-за ограничения callback_data в 64 байта вместо json-формата используется произвольный,
  который затем переводится в json функцией str_to_json() (cм. telegram_bot.py)
- Из-за этого же ограничения (наверное) callback_data должен быть латиницей., соответственно в клавиатурах
  с расписанием данные к ключам weekday на английском. (callback_to_json переводит обратно)
- По тем же причинам введены сокращения в callback_data:
    - type -> t
    - command -> c
    - place -> p
    - weekday -> wd
    - subject -> sj
    - department_id -> did
    - list_id -> lid
  Для удобного перевода payload vk-style в callback_data существует функция payload_to_callback() в этом файле
"""
import traceback

from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import json
import logging

logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)

nexus_link = 'https://t.me/science_nexus_bot'  # Периодически бота банят, так что нужно обновлять ссылку


def payload_to_callback(payload) -> str:
    """
    Переводит payload vk-клавиатуры в своеобразно стилизованный callback_data для телеграма.
    Обратная функция callback_to_json() в файле telegram_bot.py.

    Пример:
    payload={"type": "action", "command": "table_empty"}
    callback_data='t:action,a_t:message,c:table_empty'
    :param payload: входная строка или json-dict payload-а из вк
    :return: callback_data string
    """

    if type(payload) == str:
        payload = json.loads(payload)
    elif type(payload) == dict:
        pass
    else:
        raise TypeError('Передан неправильный тип данных')
    payload_item_list = ['type', 'action_type', 'command', 'place', 'weekday', 'subject', 'department_id', 'list_id']
    callback_item_list = ['t', 'a_t', 'c', 'p', 'wd', 'sj', 'did', 'lid']
    callback_data = ''
    for item in payload:
        if item in payload_item_list:
            callback_data += callback_item_list[payload_item_list.index(item)] + ':' + payload[item] + ','
        else:
            callback_data += item + ':' + payload[item] + ','
    if len(callback_data[:-1]) > 64:  # ограничение телеги на 64 байта (по сути 1 байт = 1 символ, я проверял)
        raise ValueError(f'\tУВАГА!! Слишком большой callback_data, телеграм такое не скушает. Payload: {payload}')
    return callback_data[:-1]  # последний символ - запятая, поэтому отсекаем ее


# ГЛАВНЫЕ КЛАВИАТУРЫ
# Основная клавиатура с календарем
def kb_main_cal():
    logger.info(f'Генерируем основную клавиатуру с календарем')
    markup = ReplyKeyboardMarkup(resize_keyboard=True)  # основная клавиатура - не inline
    btn_table = KeyboardButton('Расписание 🗓')  # callback_data соответственно тоже нет
    btn_cal = KeyboardButton('Календарь 📆')
    btn_literature = KeyboardButton('Литература 📚')
    btn_prepods = KeyboardButton('Преподы 👨🏼‍🏫')
    btn_other = KeyboardButton('Прочее ⚙')
    btn_links = KeyboardButton('Полезные ссылки 🔗')
    markup.row(btn_table, btn_cal)
    markup.row(btn_literature, btn_prepods)
    markup.row(btn_other, btn_links)
    logger.info(f'Основная клавиатура с календарем готова.\n')
    return markup


# Основная клавиатура без календаря
def kb_main():
    logger.info(f'Генерируем основную клавиатуру без календаря')
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    btn_table = KeyboardButton('Расписание 🗓')
    btn_literature = KeyboardButton('Литература 📚')
    btn_prepods = KeyboardButton('Преподы 👨🏼‍🏫')
    btn_other = KeyboardButton('Прочее ⚙')
    btn_links = KeyboardButton('Полезные ссылки 🔗')
    markup.row(btn_table)
    markup.row(btn_literature, btn_prepods)
    markup.row(btn_other, btn_links)
    logger.info(f'Основная клавиатура без календаря готова.\n')
    return markup


# ВЛОЖЕННЫЕ КЛАВИАТУРЫ (inline)
# Клавиатура "Расписания" пустая
def kb_table_():
    logger.info(f'Генерируем клавиатуру "Расписания" пустую')
    markup = InlineKeyboardMarkup()

    payload = {'type': 'action',
               'command': 'table_empty'}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_where = InlineKeyboardButton('Где расписание?', callback_data=callback_data)

    markup.row(btn_where)
    logger.info(f'Клавиатура "Расписания" пустая готова.\n')
    return markup


# Клавиатура "Расписания" пустая с доп. группой (точно такая же)
def kb_table__additional():
    return kb_table_()


# Клавиатура "Расписания" СЕССИЯ
def kb_table_exam():
    logger.info(f'Генерируем клавиатуру "Расписания" СЕССИЯ')
    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "table_exam"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_exam = InlineKeyboardButton('Расписание экзаменов', callback_data=callback_data)

    markup.row(btn_exam)
    logger.info(f'Клавиатура "Расписания" СЕССИЯ готова.\n')
    return markup


# Клавиатура "Расписания" СЕССИЯ additional
def kb_table_exam_additional():
    logger.info(f'Генерируем клавиатуру "Расписания" СЕССИЯ additional')
    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "table_exam"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_exam = InlineKeyboardButton('Расписание экзаменов', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_exam_2"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_exam_additional = InlineKeyboardButton('Расписание экзаменов (доп)', callback_data=callback_data)

    markup.row(btn_exam, btn_exam_additional)
    logger.info(f'Клавиатура "Расписания" СЕССИЯ additional готова.\n')
    return markup


# Клавиатура "Расписания" обычная
def kb_table_study():
    logger.info(f'Генерируем клавиатуру "Расписания" обычную')
    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "table_today"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_today = InlineKeyboardButton('Расписание на сегодня', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_tomorrow"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_tomorrow = InlineKeyboardButton('Расписание на завтра', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "table_other"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_other = InlineKeyboardButton('На другие дни', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "table_prepods"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_prepods = InlineKeyboardButton('Расписание преподавателей', callback_data=callback_data)

    markup.row(btn_today)
    markup.row(btn_tomorrow)
    markup.row(btn_other)
    markup.row(btn_prepods)

    logger.info(f'Клавиатура "Расписания" обычная готова.\n')
    return markup


# Клавиатура "Расписания" обычная additional
def kb_table_study_additional():
    logger.info(f'Генерируем клавиатуру "Расписания" обычную additional')
    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "table_today"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_today = InlineKeyboardButton('Сегодня', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_today_2"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_today_additional = InlineKeyboardButton('Сегодня (доп)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_tomorrow"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_tomorrow = InlineKeyboardButton('Завтра', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_tomorrow_2"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_tomorrow_additional = InlineKeyboardButton('Завтра (доп)', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "table_other"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_other = InlineKeyboardButton('Другие дни', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "table_other_2"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_other_additional = InlineKeyboardButton('Другие дни (доп)', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "table_prepods"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_prepods = InlineKeyboardButton('Расписание преподавателей', callback_data=callback_data)

    markup.row(btn_today, btn_today_additional)
    markup.row(btn_tomorrow, btn_tomorrow_additional)
    markup.row(btn_other, btn_other_additional)
    markup.row(btn_prepods)

    logger.info(f'Клавиатура "Расписания" обычная additional готова.\n')
    return markup


# Клавиатура "Расписания" смешанная (экзамены + расписание)
def kb_table_mixed():
    logger.info(f'Генерируем клавиатуру "Расписания" смешанную')
    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "table_exam"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_exam = InlineKeyboardButton('Расписание экзаменов', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_today"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_today = InlineKeyboardButton('Расписание на сегодня', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_tomorrow"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_tomorrow = InlineKeyboardButton('Расписание на завтра', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "table_other"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_other = InlineKeyboardButton('На другие дни', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "table_prepods"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_prepods = InlineKeyboardButton('Расписание преподавателей', callback_data=callback_data)

    markup.row(btn_exam)
    markup.row(btn_today)
    markup.row(btn_tomorrow)
    markup.row(btn_other)
    markup.row(btn_prepods)

    logger.info(f'Клавиатура "Расписания" смешанная готова.\n')
    return markup


# Клавиатура "Расписания" смешанная (экзамены + расписание) additional
def kb_table_mixed_additional():
    logger.info(f'Генерируем клавиатуру "Расписания" смешанную additional')
    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "table_exam"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_exam = InlineKeyboardButton('Экзамены', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_exam_2"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_exam_additional = InlineKeyboardButton('Экзамены (доп)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_today"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_today = InlineKeyboardButton('Сегодня', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_today_2"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_today_additional = InlineKeyboardButton('Сегодня (доп)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_tomorrow"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_tomorrow = InlineKeyboardButton('Завтра', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_tomorrow_2"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_tomorrow_additional = InlineKeyboardButton('Завтра (доп)', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "table_other"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_other = InlineKeyboardButton('Другие дни', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "table_other_2"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_other_additional = InlineKeyboardButton('Другие дни (доп)', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "table_prepods"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_prepods = InlineKeyboardButton('Расписание преподавателей', callback_data=callback_data)

    markup.row(btn_exam, btn_exam_additional)
    markup.row(btn_today, btn_today_additional)
    markup.row(btn_tomorrow, btn_tomorrow_additional)
    markup.row(btn_other, btn_other_additional)
    markup.row(btn_prepods)

    logger.info(f'Клавиатура "Расписания" смешанная additional готова.\n')
    return markup


# Клавиатура "Календарь"
def kb_calendar():
    logger.info(f'Генерируем клавиатуру "Календарь"')
    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "calendar_today"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_cal_today = InlineKeyboardButton('Календарь на сегодня', callback_data=callback_data)

    payload = {"type": "action",
               "command": "calendar_tomorrow"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_cal_tomorrow = InlineKeyboardButton('Календарь на завтра', callback_data=callback_data)

    markup.row(btn_cal_today)
    markup.row(btn_cal_tomorrow)

    logger.info(f'Клавиатура "Календарь" готова.\n')
    return markup


# Клавиатура "Прочее"
def kb_other():
    logger.info(f'Генерируем клавиатуру "Прочее"')
    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "random_anecdote"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_random_anecdote = InlineKeyboardButton('Случайный анекдот', callback_data=callback_data)

    payload = {"type": "action",
               "command": "random_toast"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_random_toast = InlineKeyboardButton('Случайный тост', callback_data=callback_data)

    payload = {"type": "action",
               "command": "anecdote_subscribe"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_anecdote_subscribe = InlineKeyboardButton('Подписаться на Анекдот', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_subscribe"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_table_subscribe = InlineKeyboardButton('Рассылка Расписания', callback_data=callback_data)

    payload = {"type": "action",
               "command": "anecdote_unsubscribe"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_anecdote_unsubscribe = InlineKeyboardButton('Отписаться от Анекдота', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_unsubscribe"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_table_unsubscribe = InlineKeyboardButton('Отписаться от Расписания', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "settings"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_settings = InlineKeyboardButton('Настройки', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "donate"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_donate = InlineKeyboardButton('Поддержать проект', callback_data=callback_data)

    markup.row(btn_random_anecdote, btn_random_toast)
    markup.row(btn_anecdote_subscribe, btn_anecdote_unsubscribe)
    markup.row(btn_table_subscribe)
    markup.row(btn_settings, btn_donate)

    logger.info(f'Клавиатура "Прочее" готова.\n')
    return markup


# Клавиатура "Полезные ссылки" с почтой
def kb_links_mail():
    logger.info(f'Генерируем клавиатуру "Полезные ссылки"')
    markup = InlineKeyboardMarkup()

    lnk_etu = InlineKeyboardButton('Сайт универа', url='https://etu.ru/')
    lnk_mail = InlineKeyboardButton('Почта', url='mail_url_placeholder')
    lnk_lk = InlineKeyboardButton('Личный кабинет', url='https://lk.etu.ru/')
    lnk_vec = InlineKeyboardButton('Мудл', url='https://vec.etu.ru/')
    lnk_lib = InlineKeyboardButton('Библиотека ЛЭТИ', url='http://library.etu.ru/')
    lnk_nexus = InlineKeyboardButton('Поиск научной лит-ры', url=nexus_link)

    markup.row(lnk_etu, lnk_mail)
    markup.row(lnk_lk, lnk_vec)
    markup.row(lnk_lib, lnk_nexus)

    logger.info(f'Клавиатура "Полезные ссылки" с почтой готова.\n')
    return markup


# Клавиатура "Полезные ссылки" без почты
def kb_links():
    logger.info(f'Генерируем клавиатуру "Полезные ссылки"')
    markup = InlineKeyboardMarkup()

    lnk_etu = InlineKeyboardButton('Сайт универа', url='https://etu.ru/')
    lnk_lk = InlineKeyboardButton('Личный кабинет', url='https://lk.etu.ru/')
    lnk_vec = InlineKeyboardButton('Мудл', url='https://vec.etu.ru/')
    lnk_lib = InlineKeyboardButton('Библиотека ЛЭТИ', url='http://library.etu.ru/')
    lnk_nexus = InlineKeyboardButton('Поиск научной лит-ры', url=nexus_link)

    markup.row(lnk_etu)
    markup.row(lnk_lk, lnk_vec)
    markup.row(lnk_lib, lnk_nexus)

    logger.info(f'Клавиатура "Полезные ссылки" без почты готова.\n')
    return markup


# Клавиатура "Расписания на другие дни"; even - чёт, odd - нечёт
# Четная неделя - "главная" (отличие в том, что текущая слева, в вк отличия в цветах!)
def kb_table_other_even():
    logger.info(f'Генерируем клавиатуру "Расписания на другие дни" чётная')
    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Monday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_monday_even = InlineKeyboardButton('Понедельник (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Monday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_monday_odd = InlineKeyboardButton('Понедельник (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Tuesday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_tuesday_even = InlineKeyboardButton('Вторник (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Tuesday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_tuesday_odd = InlineKeyboardButton('Вторник (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Wednesday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_wednesday_even = InlineKeyboardButton('Среда (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Wednesday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_wednesday_odd = InlineKeyboardButton('Среда (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Thursday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_thursday_even = InlineKeyboardButton('Четверг (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Thursday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_thursday_odd = InlineKeyboardButton('Четверг (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Friday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_friday_even = InlineKeyboardButton('Пятница (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Friday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_friday_odd = InlineKeyboardButton('Пятница (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Saturday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_saturday_even = InlineKeyboardButton('Суббота (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Saturday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_saturday_odd = InlineKeyboardButton('Суббота (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_back"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_back = InlineKeyboardButton('Назад', callback_data=callback_data)

    markup.row(btn_monday_even, btn_monday_odd)
    markup.row(btn_tuesday_even, btn_tuesday_odd)
    markup.row(btn_wednesday_even, btn_wednesday_odd)
    markup.row(btn_thursday_even, btn_thursday_odd)
    markup.row(btn_friday_even, btn_friday_odd)
    markup.row(btn_saturday_even, btn_saturday_odd)
    markup.row(btn_back)

    logger.info(f'Клавиатура "Расписания на другие дни" чётная готова.\n')
    return markup


# нечетная неделя - "главная"
def kb_table_other_odd():
    logger.info(f'Генерируем клавиатуру "Расписания на другие дни" нечётная')

    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Monday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_monday_even = InlineKeyboardButton('Понедельник (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Monday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_monday_odd = InlineKeyboardButton('Понедельник (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Tuesday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_tuesday_even = InlineKeyboardButton('Вторник (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Tuesday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_tuesday_odd = InlineKeyboardButton('Вторник (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Wednesday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_wednesday_even = InlineKeyboardButton('Среда (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Wednesday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_wednesday_odd = InlineKeyboardButton('Среда (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Thursday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_thursday_even = InlineKeyboardButton('Четверг (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Thursday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_thursday_odd = InlineKeyboardButton('Четверг (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Friday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_friday_even = InlineKeyboardButton('Пятница (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Friday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_friday_odd = InlineKeyboardButton('Пятница (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Saturday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_saturday_even = InlineKeyboardButton('Суббота (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday",
               "weekday": "Saturday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_saturday_odd = InlineKeyboardButton('Суббота (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_back"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_back = InlineKeyboardButton('Назад', callback_data=callback_data)

    markup.row(btn_monday_odd, btn_monday_even)
    markup.row(btn_tuesday_odd, btn_tuesday_even)
    markup.row(btn_wednesday_odd, btn_wednesday_even)
    markup.row(btn_thursday_odd, btn_thursday_even)
    markup.row(btn_friday_odd, btn_friday_even)
    markup.row(btn_saturday_odd, btn_saturday_even)
    markup.row(btn_back)

    logger.info(f'Клавиатура "Расписания на другие дни" нечётная готова.\n')
    return markup


# то же самое, но additional:
def kb_table_other_even_2():
    logger.info(f'Генерируем клавиатуру "Расписания на другие дни" чётная additional')
    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Monday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_monday_even = InlineKeyboardButton('Понедельник (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Monday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_monday_odd = InlineKeyboardButton('Понедельник (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Tuesday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_tuesday_even = InlineKeyboardButton('Вторник (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Tuesday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_tuesday_odd = InlineKeyboardButton('Вторник (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Wednesday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_wednesday_even = InlineKeyboardButton('Среда (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Wednesday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_wednesday_odd = InlineKeyboardButton('Среда (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Thursday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_thursday_even = InlineKeyboardButton('Четверг (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Thursday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_thursday_odd = InlineKeyboardButton('Четверг (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Friday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_friday_even = InlineKeyboardButton('Пятница (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Friday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_friday_odd = InlineKeyboardButton('Пятница (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Saturday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_saturday_even = InlineKeyboardButton('Суббота (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Saturday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_saturday_odd = InlineKeyboardButton('Суббота (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_back"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_back = InlineKeyboardButton('Назад', callback_data=callback_data)

    markup.row(btn_monday_even, btn_monday_odd)
    markup.row(btn_tuesday_even, btn_tuesday_odd)
    markup.row(btn_wednesday_even, btn_wednesday_odd)
    markup.row(btn_thursday_even, btn_thursday_odd)
    markup.row(btn_friday_even, btn_friday_odd)
    markup.row(btn_saturday_even, btn_saturday_odd)
    markup.row(btn_back)

    logger.info(f'Клавиатура "Расписания на другие дни" чётная additionalготова.\n')
    return markup


# нечетная неделя - "главная" additional
def kb_table_other_odd_2():
    logger.info(f'Генерируем клавиатуру "Расписания на другие дни" нечётная additional')

    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Monday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_monday_even = InlineKeyboardButton('Понедельник (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Monday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_monday_odd = InlineKeyboardButton('Понедельник (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Tuesday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_tuesday_even = InlineKeyboardButton('Вторник (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Tuesday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_tuesday_odd = InlineKeyboardButton('Вторник (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Wednesday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_wednesday_even = InlineKeyboardButton('Среда (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Wednesday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_wednesday_odd = InlineKeyboardButton('Среда (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Thursday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_thursday_even = InlineKeyboardButton('Четверг (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Thursday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_thursday_odd = InlineKeyboardButton('Четверг (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Friday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_friday_even = InlineKeyboardButton('Пятница (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Friday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_friday_odd = InlineKeyboardButton('Пятница (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Saturday (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_saturday_even = InlineKeyboardButton('Суббота (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_weekday_2",
               "weekday": "Saturday (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_saturday_odd = InlineKeyboardButton('Суббота (нечёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_back"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_back = InlineKeyboardButton('Назад', callback_data=callback_data)

    markup.row(btn_monday_odd, btn_monday_even)
    markup.row(btn_tuesday_odd, btn_tuesday_even)
    markup.row(btn_wednesday_odd, btn_wednesday_even)
    markup.row(btn_thursday_odd, btn_thursday_even)
    markup.row(btn_friday_odd, btn_friday_even)
    markup.row(btn_saturday_odd, btn_saturday_even)
    markup.row(btn_back)

    logger.info(f'Клавиатура "Расписания на другие дни" нечётная additional готова.\n')
    return markup


# Мини-клавиатуры

# мини-клавиатура изменения групп
def kb_change_groups():
    logger.info(f'Генерируем клавиатуру изменения групп')

    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "change_group"
               }
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_change_group = InlineKeyboardButton('Изменить основную группу', callback_data=callback_data)

    payload = {"type": "action",
               "command": "change_additional_group"
               }
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_change_additional_group = InlineKeyboardButton('Изменить дополнительную группу', callback_data=callback_data)

    markup.row(btn_change_group)
    markup.row(btn_change_additional_group)

    logger.info(f'Клавиатура изменения групп готова.\n')
    return markup


# мини-клавиатура изменения доп.группы (для модераторов и админов)
def kb_change_additional_group():
    logger.info(f'Генерируем клавиатуру изменения доп.группы')

    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "change_additional_group"
               }
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_change_additional_group = InlineKeyboardButton('Изменить дополнительную группу', callback_data=callback_data)

    markup.row(btn_change_additional_group)

    logger.info(f'Клавиатура изменения доп.группы готова.\n')
    return markup


# мини-клавиатура поиска препода
def kb_search_department():
    logger.info(f'Генерируем мини-клавиатуру поиска препода')

    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "search_prepod_text"
               }
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_search_text = InlineKeyboardButton('Поиск по фамилии', callback_data=callback_data)

    payload = {"type": "action",
               "command": "search_department",
               "list_id": str(0)  # 0 потому что первая клава
               }
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_search_department = InlineKeyboardButton('Выбор кафедры преподавателя', callback_data=callback_data)

    payload = {"type": "action",
               "command": "prepods_history"
               }
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_history = InlineKeyboardButton('История поиска', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_back"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_back = InlineKeyboardButton('Расписание группы', callback_data=callback_data)

    markup.row(btn_search_text)
    markup.row(btn_search_department)
    markup.row(btn_history)
    markup.row(btn_back)

    logger.info(f'Клавиатура выбора кафедры препода готова.\n')
    return markup


# мини-клавиатура миниигр
def kb_minigames():
    logger.info(f'Генерируем мини-клавиатуру миниигр')

    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "heads_or_tails_toss"
               }
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_heads_or_nails = InlineKeyboardButton('Орел или решка?', callback_data=callback_data)

    payload = {"type": "action",
               "command": "start_classical_RPC"
               }
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_RPC = InlineKeyboardButton('Камень-ножницы-бумага с ботом', callback_data=callback_data)

    payload = {"type": "action",
               "command": "start_multi_RPC"
               }
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_RPC_multi = InlineKeyboardButton('Камень-ножницы-бумага с человеком', callback_data=callback_data)

    markup.row(btn_heads_or_nails)
    markup.row(btn_RPC)
    # markup.row(btn_RPC_multi)
    logger.info(f'Клавиатура миниигр готова.\n')
    return markup


# мини-клавиатура перекидывания решки
def kb_heads_or_tails_retoss():
    logger.info(f'Генерируем мини-клавиатуру перекидывания решки')

    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "heads_or_tails_toss"
               }
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_retoss = InlineKeyboardButton('Бросить ещё раз', callback_data=callback_data)

    payload = {"type": "action",
               "command": "minigames"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_back = InlineKeyboardButton('Вернуться в мини-игры', callback_data=callback_data)

    markup.row(btn_retoss)
    markup.row(btn_back)

    logger.info(f'Клавиатура перекидывания решки готова.\n')
    return markup


def kb_table_settings():
    """
    Клавиатура настройки рассылки расписаний (kb_table_settings)

    доступные опции:
    - Время отправки
    - Тип рассылки (ежедневная/еженедельная/обе)
    - TODO Тип сообщения (полные названия предметов и ФИО или как сейчас - сокращенная информация)
    другие кнопки:
    - Отписаться от рассылки
    - Назад
    """
    logger.info(f'Генерируем мини-клавиатуру настройки рассылки расписаний')

    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "set_tables_mode"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_table_set_mode = InlineKeyboardButton('Тип рассылки', callback_data=callback_data)

    payload = {"type": "action",
               "command": "set_tables_time"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_table_set_time = InlineKeyboardButton('Время рассылки', callback_data=callback_data)

    # payload = {"type": "action",
    #            "command": "set_tables_mode"}
    # callback_data = payload_to_callback(payload)
    # logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    # btn_table_set_format = InlineKeyboardButton('Формат рассылки', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_unsubscribe"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_table_unsubscribe = InlineKeyboardButton('Отписаться', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "other"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_table_back = InlineKeyboardButton('Назад', callback_data=callback_data)

    markup.row(btn_table_set_mode)
    markup.row(btn_table_set_time)
    # markup.row(btn_table_set_format)
    markup.row(btn_table_unsubscribe)
    markup.row(btn_table_back)

    logger.info(f'Клавиатура настройки рассылок готова.\n')
    return markup


def kb_set_tables_mode():
    """
    Клавиатура настройки рассылки расписаний (set_tables_mode)
    Кнопки:
    - Тип рассылки (ежедневная/еженедельная/обе)
    - Назад
    """
    logger.info(f'Генерируем мини-клавиатуру настройки режима рассылки расписаний')

    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "t_mode_set",
               "mode": "daily"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_table_set_mode_day = InlineKeyboardButton('Ежедневно', callback_data=callback_data)

    payload = {"type": "action",
               "command": "t_mode_set",
               "mode": "weekly"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_table_set_mode_week = InlineKeyboardButton('Еженедельно', callback_data=callback_data)

    payload = {"type": "action",
               "command": "t_mode_set",
               "mode": "both"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_table_set_mode_mix = InlineKeyboardButton('Оба', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "table_settings"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_table_back = InlineKeyboardButton('Назад', callback_data=callback_data)

    markup.row(btn_table_set_mode_day)
    markup.row(btn_table_set_mode_week)
    markup.row(btn_table_set_mode_mix)
    markup.row(btn_table_back)

    logger.info(f'Клавиатура настройки рассылок готова.\n')
    return markup


def kb_set_tables_mode_cal():
    """
    Клавиатура настройки рассылки расписаний (set_tables_mode) с опцией выбора Календаря
    Кнопки:
    - Тип рассылки (ежедневная/еженедельная/обе)
    - Назад
    """
    logger.info(f'Генерируем мини-клавиатуру настройки режима рассылки расписаний')

    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "t_mode_set",
               "mode": "calendar"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_table_set_mode_cal = InlineKeyboardButton('Календарь', callback_data=callback_data)

    payload = {"type": "action",
               "command": "t_mode_set",
               "mode": "daily"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_table_set_mode_day = InlineKeyboardButton('Ежедневно', callback_data=callback_data)

    payload = {"type": "action",
               "command": "t_mode_set",
               "mode": "weekly"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_table_set_mode_week = InlineKeyboardButton('Еженедельно', callback_data=callback_data)

    payload = {"type": "action",
               "command": "t_mode_set",
               "mode": "both"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_table_set_mode_mix = InlineKeyboardButton('Оба', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "table_settings"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_table_back = InlineKeyboardButton('Назад', callback_data=callback_data)

    markup.row(btn_table_set_mode_cal)
    markup.row(btn_table_set_mode_day)
    markup.row(btn_table_set_mode_week)
    markup.row(btn_table_set_mode_mix)
    markup.row(btn_table_back)

    logger.info(f'Клавиатура настройки рассылок готова.\n')
    return markup


# огромная клавиатура с кнопками для расписания преподов. создается при импорте
def kb_prepod_schedule(prepod_id, day):
    markup = InlineKeyboardMarkup()

    rus_to_eng_days = {'Понедельник (чёт)': 'Monday (even)',
                       'Понедельник (нечёт)': 'Monday (odd)',
                       'Вторник (чёт)': 'Tuesday (even)',
                       'Вторник (нечёт)': 'Tuesday (odd)',
                       'Среда (чёт)': 'Wednesday (even)',
                       'Среда (нечёт)': 'Wednesday (odd)',
                       'Четверг (чёт)': 'Thursday (even)',
                       'Четверг (нечёт)': 'Thursday (odd)',
                       'Пятница (чёт)': 'Friday (even)',
                       'Пятница (нечёт)': 'Friday (odd)',
                       'Суббота (чёт)': 'Saturday (even)',
                       'Суббота (нечёт)': 'Saturday (odd)',
                       'Воскресенье (чёт)': 'Sunday (even)',
                       'Воскресенье (нечёт)': 'Sunday (odd)',
                       'full (чёт)': 'week (even)',
                       'full (нечёт)': 'week (odd)'}

    day = rus_to_eng_days[day]

    payload = {"type": "action",
               "command": "table_prepod",
               "id": str(prepod_id),
               "weekday": day}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_today = InlineKeyboardButton('Расписание на сегодня', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_prepod",
               "id": str(prepod_id),
               "weekday": "week (even)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_week_even = InlineKeyboardButton('Вся неделя (чёт)', callback_data=callback_data)

    payload = {"type": "action",
               "command": "table_prepod",
               "id": str(prepod_id),
               "weekday": "week (odd)"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_week_odd = InlineKeyboardButton('Вся неделя (нечёт)', callback_data=callback_data)

    payload = {"type": "navigation",
               "place": "table_prepods"}
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_back = InlineKeyboardButton('Назад', callback_data=callback_data)

    markup.row(btn_today)
    markup.row(btn_week_odd, btn_week_even)
    markup.row(btn_back)

    return markup


# мини-клавиатура отмены ввода данных от ЛК
def kb_cancel_set_lk_secrets():
    logger.info(f'Генерируем мини-клавиатуру отмены ввода данных от ЛК')

    markup = InlineKeyboardMarkup()

    payload = {"type": "action",
               "command": "cancel_set_lk_secrets"
               }
    callback_data = payload_to_callback(payload)
    logger.info(f'Перевод payload в callback_data: {len(callback_data)} символа \n\t{payload}\n\t->\n\t{callback_data}')
    btn_cancel = InlineKeyboardButton('Отмена', callback_data=callback_data)
    markup.row(btn_cancel)
    logger.info(f'Клавиатура отмены ввода данных от ЛК готова.\n')
    return markup


if __name__ == '__main__':
    keyboards = [
        'kb_main_cal',
        'kb_main',
        'kb_table_',
        'kb_table__additional',
        'kb_table_exam',
        'kb_table_exam_additional',
        'kb_table_study',
        'kb_table_study_additional',
        'kb_table_mixed',
        'kb_table_mixed_additional',
        'kb_calendar',
        'kb_other',
        'kb_links_mail',
        'kb_links',
        'kb_table_other_even',
        'kb_table_other_even_2',
        'kb_table_other_odd',
        'kb_table_other_odd_2',
        'kb_change_groups',
        'kb_change_additional_group',
        'kb_search_department',
        'kb_minigames',
        'kb_heads_or_tails_retoss',
        'kb_table_settings',
        'kb_set_tables_mode',
        'kb_set_tables_mode_cal',
        'kb_cancel_set_lk_secrets'
    ]
    for keyboard in keyboards:
        try:
            with open(f'{keyboard}.json', 'w', encoding='utf-8') as f:
                f.write(json.dumps(json.loads(eval(keyboard)().to_json()), ensure_ascii=False, indent=4))
        except:
            logger.critical(f'Ошибка при генерации клавиатуры {keyboard}\ntraceback: {traceback.format_exc()}')
