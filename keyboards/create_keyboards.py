from vk_api.keyboard import VkKeyboard, VkKeyboardColor

"""
Здесь находится код для генерации всех клавиатур, общих для пользователей бота
"""

# ГЛАВНЫЕ КЛАВИАТУРЫ
# Основная клавиатура с календарем и почтой
keyboard_main_mail_cal = VkKeyboard(one_time=False)
keyboard_main_mail_cal.add_button('Расписание', color=VkKeyboardColor.POSITIVE,
                                  payload={"type": "navigation",
                                           "place": "table"})
keyboard_main_mail_cal.add_button('Календарь', color=VkKeyboardColor.POSITIVE,
                                  payload={"type": "navigation",
                                           "place": "calendar"})  # или это пихнуть в расписание
keyboard_main_mail_cal.add_line()
keyboard_main_mail_cal.add_button('Методички', color=VkKeyboardColor.PRIMARY,
                                  payload={"type": "navigation",
                                           "place": "books"})
keyboard_main_mail_cal.add_button('Преподы', color=VkKeyboardColor.PRIMARY,
                                  payload={"type": "navigation",
                                           "place": "prepods"})

keyboard_main_mail_cal.add_line()
keyboard_main_mail_cal.add_openlink_button('Личный кабинет', link='https://lk.etu.ru')
keyboard_main_mail_cal.add_openlink_button('Почта группы', link='mail_url_placeholder')
keyboard_main_mail_cal.add_line()
keyboard_main_mail_cal.add_button('Прочее', color=VkKeyboardColor.NEGATIVE,
                                  payload={"type": "navigation",
                                           "place": "other"})
keyboard_main_mail_cal.add_openlink_button('Мудл', link='https://vec.etu.ru')

# Основная клавиатура без календаря и с почтой
keyboard_main_mail = VkKeyboard(one_time=False)
keyboard_main_mail.add_button('Расписание', color=VkKeyboardColor.POSITIVE,
                              payload={"type": "navigation",
                                       "place": "table"})
keyboard_main_mail.add_line()
keyboard_main_mail.add_button('Методички', color=VkKeyboardColor.PRIMARY,
                              payload={"type": "navigation",
                                       "place": "books"})
keyboard_main_mail.add_button('Преподы', color=VkKeyboardColor.PRIMARY,
                              payload={"type": "navigation",
                                       "place": "prepods"})
keyboard_main_mail.add_line()
keyboard_main_mail.add_openlink_button('Личный кабинет', link='https://lk.etu.ru')
keyboard_main_mail.add_openlink_button('Почта группы', link='mail_url_placeholder')
keyboard_main_mail.add_line()
keyboard_main_mail.add_button('Прочее', color=VkKeyboardColor.NEGATIVE,
                              payload={"type": "navigation",
                                       "place": "other"})
keyboard_main_mail.add_openlink_button('Мудл', link='https://vec.etu.ru')

# Основная клавиатура без почты с календарем
keyboard_main_cal = VkKeyboard(one_time=False)
keyboard_main_cal.add_button('Расписание', color=VkKeyboardColor.POSITIVE,
                             payload={"type": "navigation",
                                      "place": "table"})
keyboard_main_cal.add_button('Календарь', color=VkKeyboardColor.POSITIVE,
                             payload={"type": "navigation",
                                      "place": "calendar"})
keyboard_main_cal.add_line()
keyboard_main_cal.add_button('Методички', color=VkKeyboardColor.PRIMARY,
                             payload={"type": "navigation",
                                      "place": "books"})
keyboard_main_cal.add_button('Преподы', color=VkKeyboardColor.PRIMARY,
                             payload={"type": "navigation",
                                      "place": "prepods"})
keyboard_main_cal.add_line()
keyboard_main_cal.add_openlink_button('Личный кабинет', link='https://lk.etu.ru')
keyboard_main_cal.add_openlink_button('Мудл', link='https://vec.etu.ru')
keyboard_main_cal.add_line()
keyboard_main_cal.add_button('Прочее', color=VkKeyboardColor.NEGATIVE,
                             payload={"type": "navigation",
                                      "place": "other"})

# Основная клавиатура без почты и календаря
keyboard_main = VkKeyboard(one_time=False)
keyboard_main.add_button('Расписание', color=VkKeyboardColor.POSITIVE,
                         payload={"type": "navigation",
                                  "place": "table"})
keyboard_main.add_line()
keyboard_main.add_button('Методички', color=VkKeyboardColor.PRIMARY,
                         payload={"type": "navigation",
                                  "place": "books"})
keyboard_main.add_button('Преподы', color=VkKeyboardColor.PRIMARY,
                         payload={"type": "navigation",
                                  "place": "prepods"})

keyboard_main.add_line()
keyboard_main.add_openlink_button('Личный кабинет', link='https://lk.etu.ru')
keyboard_main.add_openlink_button('Мудл', link='https://vec.etu.ru')
keyboard_main.add_line()
keyboard_main.add_button('Прочее', color=VkKeyboardColor.NEGATIVE,
                         payload={"type": "navigation",
                                  "place": "other"})

# Те же клавиатуры, только для периода сессии TODO
'''keyboard_main_mail_cal = VkKeyboard(one_time=False)
keyboard_main_mail_cal.add_button('Расписание', color=VkKeyboardColor.NEGATIVE,
                                  payload={"type": "navigation",
                                           "place": "table"})
keyboard_main_mail_cal.add_button('Методички', color=VkKeyboardColor.PRIMARY,
                                  payload={"type": "navigation",
                                           "place": "books"})
keyboard_main_mail_cal.add_button('Преподы', color=VkKeyboardColor.POSITIVE,
                                  payload={"type": "navigation",
                                           "place": "prepods"})
keyboard_main_mail_cal.add_line()
keyboard_main_mail_cal.add_button('Календарь', color=VkKeyboardColor.SECONDARY,
                                  payload={"type": "navigation",
                                           "place": "calendar"})
keyboard_main_mail_cal.add_openlink_button('Мудл', link='https://vec.etu.ru')
keyboard_main_mail_cal.add_line()
keyboard_main_mail_cal.add_openlink_button('Личный кабинет', link='https://lk.etu.ru')
keyboard_main_mail_cal.add_openlink_button('Почта группы', link='mail_url_placeholder')
keyboard_main_mail_cal.add_line()
keyboard_main_mail_cal.add_button('Прочее', color=VkKeyboardColor.NEGATIVE,
                                  payload={"type": "navigation",
                                           "place": "other"})


# Основная клавиатура без календаря и с почтой
keyboard_main_mail = VkKeyboard(one_time=False)
keyboard_main_mail.add_button('Расписание', color=VkKeyboardColor.NEGATIVE,
                              payload={"type": "navigation",
                                       "place": "table"})
keyboard_main_mail.add_button('Методички', color=VkKeyboardColor.PRIMARY,
                              payload={"type": "navigation",
                                       "place": "books"})
keyboard_main_mail.add_line()
keyboard_main_mail.add_openlink_button('Почта группы', link='mail_url_placeholder')
keyboard_main_mail.add_button('Преподы', color=VkKeyboardColor.POSITIVE,
                              payload={"type": "navigation",
                                       "place": "prepods"})
keyboard_main_mail.add_line()
keyboard_main_mail.add_openlink_button('Мудл', link='https://vec.etu.ru')
keyboard_main_mail.add_openlink_button('Личный кабинет', link='https://lk.etu.ru')
keyboard_main_mail.add_line()
keyboard_main_mail.add_button('Прочее', color=VkKeyboardColor.NEGATIVE,
                              payload={"type": "navigation",
                                       "place": "other"})


# Основная клавиатура без почты с календарем
keyboard_main_cal = VkKeyboard(one_time=False)
keyboard_main_cal.add_button('Расписание', color=VkKeyboardColor.NEGATIVE,
                             payload={"type": "navigation",
                                      "place": "table"})
keyboard_main_cal.add_button('Календарь', color=VkKeyboardColor.SECONDARY,
                             payload={"type": "navigation",
                                      "place": "calendar"})
keyboard_main_cal.add_line()
keyboard_main_cal.add_button('Методички', color=VkKeyboardColor.PRIMARY,
                             payload={"type": "navigation",
                                      "place": "books"})
keyboard_main_cal.add_button('Преподы', color=VkKeyboardColor.POSITIVE,
                             payload={"type": "navigation",
                                      "place": "prepods"})
keyboard_main_cal.add_line()
keyboard_main_cal.add_openlink_button('Мудл', link='https://vec.etu.ru')
keyboard_main_cal.add_openlink_button('Личный кабинет', link='https://lk.etu.ru')
keyboard_main_cal.add_line()
keyboard_main_cal.add_button('Прочее', color=VkKeyboardColor.NEGATIVE,
                             payload={"type": "navigation",
                                      "place": "other"})


# Основная клавиатура без почты и календаря
keyboard_main = VkKeyboard(one_time=False)
keyboard_main.add_button('Расписание', color=VkKeyboardColor.NEGATIVE,
                         payload={"type": "navigation",
                                  "place": "table"})
keyboard_main.add_line()
keyboard_main.add_button('Методички', color=VkKeyboardColor.PRIMARY,
                         payload={"type": "navigation",
                                  "place": "books"})
keyboard_main.add_button('Преподы', color=VkKeyboardColor.POSITIVE,
                         payload={"type": "navigation",
                                  "place": "prepods"})

keyboard_main.add_line()
keyboard_main.add_openlink_button('Мудл', link='https://vec.etu.ru')
keyboard_main.add_openlink_button('Личный кабинет', link='https://lk.etu.ru')
keyboard_main.add_line()
keyboard_main.add_button('Прочее', color=VkKeyboardColor.NEGATIVE,
                         payload={"type": "navigation",
                                  "place": "other"})'''

# ВЛОЖЕННЫЕ КЛАВИАТУРЫ
# Клавиатура "Расписания" пустая
keyboard_table_ = VkKeyboard(one_time=False)
keyboard_table_.add_button('Где расписание?', color=VkKeyboardColor.NEGATIVE,
                           payload={"type": "action",
                                    "action_type": "message",
                                    "command": "table_empty"})
keyboard_table_.add_line()
keyboard_table_.add_button('Вернуться в начало',
                           payload={"type": "navigation",
                                    "place": "main"})

# Клавиатура "Расписания" СЕССИЯ
keyboard_table_exam = VkKeyboard(one_time=False)
keyboard_table_exam.add_button('Расписание экзаменов', color=VkKeyboardColor.NEGATIVE,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": "table_exam"})
keyboard_table_exam.add_line()
keyboard_table_exam.add_button('Вернуться в начало',
                               payload={"type": "navigation",
                                        "place": "main"})

# Клавиатура "Расписания" обычная
keyboard_table_study = VkKeyboard(one_time=False)
keyboard_table_study.add_button('Расписание на сегодня', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_today"})
keyboard_table_study.add_line()
keyboard_table_study.add_button('Расписание на завтра', color=VkKeyboardColor.SECONDARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_tomorrow"})
keyboard_table_study.add_line()
keyboard_table_study.add_button('На другие дни', color=VkKeyboardColor.NEGATIVE,
                                payload={"type": "navigation",
                                         "place": "table_other"})
keyboard_table_study.add_line()
keyboard_table_study.add_button('Вернуться в начало',
                                payload={"type": "navigation",
                                         "place": "main"})

# Клавиатура "Расписания" смешанная (экзамены + расписание)
keyboard_table_mixed = VkKeyboard(one_time=False)
keyboard_table_mixed.add_button('Расписание экзаменов', color=VkKeyboardColor.NEGATIVE,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_exam"})
keyboard_table_mixed.add_line()
keyboard_table_mixed.add_button('Расписание на сегодня', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_today"})
keyboard_table_mixed.add_line()
keyboard_table_mixed.add_button('Расписание на завтра', color=VkKeyboardColor.SECONDARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_tomorrow"})
keyboard_table_mixed.add_line()
keyboard_table_mixed.add_button('На другие дни', color=VkKeyboardColor.NEGATIVE,
                                payload={"type": "navigation",
                                         "place": "table_other"})
keyboard_table_mixed.add_line()
keyboard_table_mixed.add_button('Вернуться в начало',
                                payload={"type": "navigation",
                                         "place": "main"})

# Клавиатура "Календарь"
keyboard_calendar = VkKeyboard(one_time=False)
keyboard_calendar.add_button('Календарь на сегодня', color=VkKeyboardColor.POSITIVE,
                             payload={"type": "action",
                                      "action_type": "message",
                                      "command": "calendar_today"})
keyboard_calendar.add_line()
keyboard_calendar.add_button('Календарь на завтра', color=VkKeyboardColor.POSITIVE,
                             payload={"type": "action",
                                      "action_type": "message",
                                      "command": "calendar_tomorrow"})
keyboard_calendar.add_line()
keyboard_calendar.add_button('Вернуться в начало',
                             payload={"type": "navigation",
                                      "place": "main"})

# Клавиатура "Прочее"
keyboard_other = VkKeyboard(one_time=False)
keyboard_other.add_button('Случайный анекдот', color=VkKeyboardColor.POSITIVE,
                          payload={"type": "action",
                                   "action_type": "message",
                                   "command": "random_anecdote"})
keyboard_other.add_button('Случайный тост', color=VkKeyboardColor.POSITIVE,
                          payload={"type": "action",
                                   "action_type": "message",
                                   "command": "random_toast"})
keyboard_other.add_line()
keyboard_other.add_button('Подписаться на Анекдот', color=VkKeyboardColor.SECONDARY,
                          payload={"type": "action",
                                   "action_type": "message",
                                   "command": "anecdote_subscribe"})
keyboard_other.add_button('Отписаться от Анекдота', color=VkKeyboardColor.SECONDARY,
                          payload={"type": "action",
                                   "action_type": "message",
                                   "command": "anecdote_unsubscribe"})
keyboard_other.add_line()
keyboard_other.add_button('Рассылка Расписания', color=VkKeyboardColor.SECONDARY,
                          payload={"type": "navigation",
                                   "place": "kb_table_settings_sub"})
keyboard_other.add_line()
keyboard_other.add_button('Настройки', color=VkKeyboardColor.NEGATIVE,
                          payload={"type": "navigation",
                                   "place": "settings"})
keyboard_other.add_button('Telegram', color=VkKeyboardColor.PRIMARY,
                          payload={"type": "action",
                                   "action_type": "message",
                                   "command": "link_tg"})
keyboard_other.add_line()
keyboard_other.add_button('Поддержать проект', color=VkKeyboardColor.POSITIVE,
                          payload={"type": "navigation",
                                   "place": "donate"})
keyboard_other.add_line()
keyboard_other.add_button('Вернуться в начало',
                          payload={"type": "navigation",
                                   "place": "main"})

# Клавиатура "Настройки рассылки расписания"; кнопки - тип, время, отписаться, назад
kb_table_settings = VkKeyboard(one_time=False)
kb_table_settings.add_button('Тип', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "navigation",
                                         "place": "table_settings_type"})
kb_table_settings.add_button('Время', color=VkKeyboardColor.PRIMARY,
                                  payload={"type": "action",
                                           "action_type": "shiza",
                                           "target": "table_settings_time"})
kb_table_settings.add_line()
kb_table_settings.add_button('Отписаться', color=VkKeyboardColor.NEGATIVE,
                                  payload={"type": "action",
                                           "action_type": "message",
                                           "command": "table_unsubscribe"})
kb_table_settings.add_line()
kb_table_settings.add_button('Назад', color=VkKeyboardColor.NEGATIVE,
                                        payload={"type": "navigation",
                                                 "place": "other"})

# Клавиатура "Настройки типа рассылки расписания"; кнопки - ежедневно, еженедельно, обе, назад
kb_table_settings_type = VkKeyboard(one_time=False)
kb_table_settings_type.add_button('Ежедневно', color=VkKeyboardColor.PRIMARY,
                                  payload={"type": "action",
                                           "action_type": "message",
                                           "command": "table_set_type",
                                           "arg": "daily"})
kb_table_settings_type.add_button('Еженедельно', color=VkKeyboardColor.PRIMARY,
                                  payload={"type": "action",
                                           "action_type": "message",
                                           "command": "table_set_type",
                                           "arg": "weekly"})
kb_table_settings_type.add_line()
kb_table_settings_type.add_button('Оба', color=VkKeyboardColor.PRIMARY,
                                  payload={"type": "action",
                                           "action_type": "message",
                                           "command": "table_set_type",
                                           "arg": "monthly"})
kb_table_settings_type.add_line()
kb_table_settings_type.add_button('Назад', color=VkKeyboardColor.NEGATIVE,
                                        payload={"type": "navigation",
                                                 "place": "kb_table_settings"})

# Клавиатура "Расписания на другие дни"; even - чёт, odd - нечёт
# Четная неделя - "главная"
kb_table_other_even = VkKeyboard(one_time=False)
kb_table_other_even.add_button('Понедельник (чёт)', color=VkKeyboardColor.PRIMARY,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": "table_weekday",
                                        "weekday": "Понедельник (чёт)"})
kb_table_other_even.add_button('Понедельник (нечёт)', color=VkKeyboardColor.SECONDARY,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": "table_weekday",
                                        "weekday": "Понедельник (нечёт)"})
kb_table_other_even.add_line()
kb_table_other_even.add_button('Вторник (чёт)', color=VkKeyboardColor.PRIMARY,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": "table_weekday",
                                        "weekday": "Вторник (чёт)"})
kb_table_other_even.add_button('Вторник (нечёт)', color=VkKeyboardColor.SECONDARY,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": "table_weekday",
                                        "weekday": "Вторник (нечёт)"})
kb_table_other_even.add_line()
kb_table_other_even.add_button('Среда (чёт)', color=VkKeyboardColor.PRIMARY,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": "table_weekday",
                                        "weekday": "Среда (чёт)"})
kb_table_other_even.add_button('Среда (нечёт)', color=VkKeyboardColor.SECONDARY,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": "table_weekday",
                                        "weekday": "Среда (нечёт)"})
kb_table_other_even.add_line()
kb_table_other_even.add_button('Четверг (чёт)', color=VkKeyboardColor.PRIMARY,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": "table_weekday",
                                        "weekday": "Четверг (чёт)"})
kb_table_other_even.add_button('Четверг (нечёт)', color=VkKeyboardColor.SECONDARY,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": "table_weekday",
                                        "weekday": "Четверг (нечёт)"})
kb_table_other_even.add_line()
kb_table_other_even.add_button('Пятница (чёт)', color=VkKeyboardColor.PRIMARY,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": "table_weekday",
                                        "weekday": "Пятница (чёт)"})
kb_table_other_even.add_button('Пятница (нечёт)', color=VkKeyboardColor.SECONDARY,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": "table_weekday",
                                        "weekday": "Пятница (нечёт)"})
kb_table_other_even.add_line()
kb_table_other_even.add_button('Суббота (чёт)', color=VkKeyboardColor.PRIMARY,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": "table_weekday",
                                        "weekday": "Суббота (чёт)"})
kb_table_other_even.add_button('Суббота (нечёт)', color=VkKeyboardColor.SECONDARY,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": "table_weekday",
                                        "weekday": "Суббота (нечёт)"})
kb_table_other_even.add_line()
kb_table_other_even.add_button('Вернуться в расписания', color=VkKeyboardColor.POSITIVE,
                               payload={"type": "navigation",
                                        "place": "table"})
kb_table_other_even.add_button('Вернуться в начало',
                               payload={"type": "navigation",
                                        "place": "main"})

# нечетная неделя - "главная"
kb_table_other_odd = VkKeyboard(one_time=False)
kb_table_other_odd.add_button('Понедельник (чёт)', color=VkKeyboardColor.SECONDARY,
                              payload={"type": "action",
                                       "action_type": "message",
                                       "command": "table_weekday",
                                       "weekday": "Понедельник (чёт)"})
kb_table_other_odd.add_button('Понедельник (нечёт)', color=VkKeyboardColor.PRIMARY,
                              payload={"type": "action",
                                       "action_type": "message",
                                       "command": "table_weekday",
                                       "weekday": "Понедельник (нечёт)"})
kb_table_other_odd.add_line()
kb_table_other_odd.add_button('Вторник (чёт)', color=VkKeyboardColor.SECONDARY,
                              payload={"type": "action",
                                       "action_type": "message",
                                       "command": "table_weekday",
                                       "weekday": "Вторник (чёт)"})
kb_table_other_odd.add_button('Вторник (нечёт)', color=VkKeyboardColor.PRIMARY,
                              payload={"type": "action",
                                       "action_type": "message",
                                       "command": "table_weekday",
                                       "weekday": "Вторник (нечёт)"})
kb_table_other_odd.add_line()
kb_table_other_odd.add_button('Среда (чёт)', color=VkKeyboardColor.SECONDARY,
                              payload={"type": "action",
                                       "action_type": "message",
                                       "command": "table_weekday",
                                       "weekday": "Среда (чёт)"})
kb_table_other_odd.add_button('Среда (нечёт)', color=VkKeyboardColor.PRIMARY,
                              payload={"type": "action",
                                       "action_type": "message",
                                       "command": "table_weekday",
                                       "weekday": "Среда (нечёт)"})
kb_table_other_odd.add_line()
kb_table_other_odd.add_button('Четверг (чёт)', color=VkKeyboardColor.SECONDARY,
                              payload={"type": "action",
                                       "action_type": "message",
                                       "command": "table_weekday",
                                       "weekday": "Четверг (чёт)"})
kb_table_other_odd.add_button('Четверг (нечёт)', color=VkKeyboardColor.PRIMARY,
                              payload={"type": "action",
                                       "action_type": "message",
                                       "command": "table_weekday",
                                       "weekday": "Четверг (нечёт)"})
kb_table_other_odd.add_line()
kb_table_other_odd.add_button('Пятница (чёт)', color=VkKeyboardColor.SECONDARY,
                              payload={"type": "action",
                                       "action_type": "message",
                                       "command": "table_weekday",
                                       "weekday": "Пятница (чёт)"})
kb_table_other_odd.add_button('Пятница (нечёт)', color=VkKeyboardColor.PRIMARY,
                              payload={"type": "action",
                                       "action_type": "message",
                                       "command": "table_weekday",
                                       "weekday": "Пятница (нечёт)"})
kb_table_other_odd.add_line()
kb_table_other_odd.add_button('Суббота (чёт)', color=VkKeyboardColor.SECONDARY,
                              payload={"type": "action",
                                       "action_type": "message",
                                       "command": "table_weekday",
                                       "weekday": "Суббота (чёт)"})
kb_table_other_odd.add_button('Суббота (нечёт)', color=VkKeyboardColor.PRIMARY,
                              payload={"type": "action",
                                       "action_type": "message",
                                       "command": "table_weekday",
                                       "weekday": "Суббота (нечёт)"})
kb_table_other_odd.add_line()
kb_table_other_odd.add_button('Вернуться в расписания', color=VkKeyboardColor.POSITIVE,
                              payload={"type": "navigation",
                                       "place": "table"})
kb_table_other_odd.add_button('Вернуться в начало',
                              payload={"type": "navigation",
                                       "place": "main"})

# КЛАВИАТУРЫ НАСТРОЕК

# мини-клавиатура для настройки уведомлений о неизвестной команде, для всех пользователей
false_command_keyboard = VkKeyboard(one_time=False, inline=True)
false_command_keyboard.add_button(label='Ясно, не показывать это', color=VkKeyboardColor.POSITIVE,
                                  payload={"type": "action", "action_type": "message",
                                           "command": "remove_notifications"})

# Клавиатура смены группы при ошибке группы
keyboard_change_group = VkKeyboard(one_time=False, inline=True)
keyboard_change_group.add_button(label='Изменить группу', color=VkKeyboardColor.POSITIVE,
                                 payload={"type": "action",
                                          "action_type": "shiza",
                                          "target": "change_group"})

# Клавиатура настроек для адимнов
keyboard_settings_admin = VkKeyboard(one_time=False)
keyboard_settings_admin.add_button('Изменить доп. группу', color=VkKeyboardColor.PRIMARY,
                                   payload={"type": "action",
                                            "action_type": "shiza",
                                            "target": "change_additional_group"})
keyboard_settings_admin.add_line()
keyboard_settings_admin.add_button('Работа с БД', color=VkKeyboardColor.PRIMARY,
                                   payload={"type": "action",
                                            "action_type": "shiza",
                                            "target": "edit_database"})
keyboard_settings_admin.add_button('Работа с админскими БД', color=VkKeyboardColor.NEGATIVE,
                                   payload={"type": "action",
                                            "action_type": "shiza",
                                            "target": "edit_admin_database"})
keyboard_settings_admin.add_line()
keyboard_settings_admin.add_button('Вернуться в Прочее',
                                   payload={"type": "navigation",
                                            "place": "other"})
keyboard_settings_admin.add_button('Вернуться в начало',
                                   payload={"type": "navigation",
                                            "place": "main"})

# Клавиатура настроек для модеров
keyboard_settings_moderator = VkKeyboard(one_time=False)
keyboard_settings_moderator.add_button('Изменить доп. группу', color=VkKeyboardColor.PRIMARY,
                                       payload={"type": "action",
                                                "action_type": "shiza",
                                                "target": "change_additional_group"})
keyboard_settings_moderator.add_line()
keyboard_settings_moderator.add_button('Работа с БД', color=VkKeyboardColor.PRIMARY,
                                       payload={"type": "action",
                                                "action_type": "shiza",
                                                "target": "edit_database"})
keyboard_settings_moderator.add_line()
keyboard_settings_moderator.add_button('Добавление в чат', color=VkKeyboardColor.SECONDARY,
                                       payload={"type": "action",
                                                "action_type": "message",
                                                "command": "add_chat"})
keyboard_settings_moderator.add_line()
keyboard_settings_moderator.add_button('Вернуться в Прочее',
                                       payload={"type": "navigation",
                                                "place": "other"})
keyboard_settings_moderator.add_button('Вернуться в начало',
                                       payload={"type": "navigation",
                                                "place": "main"})

# клавиатура настроек (смена группы) для обычных пользователей
keyboard_settings_user = VkKeyboard(one_time=False)
keyboard_settings_user.add_button('Изменить группу', color=VkKeyboardColor.PRIMARY,
                                  payload={"type": "action",
                                           "action_type": "shiza",
                                           "target": "change_group"})
keyboard_settings_user.add_line()
keyboard_settings_user.add_button('Изменить доп. группу', color=VkKeyboardColor.PRIMARY,
                                  payload={"type": "action",
                                           "action_type": "shiza",
                                           "target": "change_additional_group"})
keyboard_settings_user.add_line()
keyboard_settings_user.add_button('Добавление в чат', color=VkKeyboardColor.SECONDARY,
                                  payload={"type": "action",
                                           "action_type": "message",
                                           "command": "add_chat"})
keyboard_settings_user.add_line()
keyboard_settings_user.add_button('Вернуться в Прочее',
                                  payload={"type": "navigation",
                                           "place": "other"})
keyboard_settings_user.add_button('Вернуться в начало',
                                  payload={"type": "navigation",
                                           "place": "main"})

# клавиатура настроек премиум-функций - пока это день дня и тосты
keyboard_settings_donator = VkKeyboard(one_time=False)
keyboard_settings_donator.add_button('Ежедневная пикча', color=VkKeyboardColor.POSITIVE,
                                     payload={"type": "action",
                                              "action_type": "message",
                                              "command": "day_of_day_toggle"})
keyboard_settings_donator.add_line()
keyboard_settings_donator.add_button('Еженедельный тост', color=VkKeyboardColor.POSITIVE,
                                     payload={"type": "action",
                                              "action_type": "message",
                                              "command": "weekly_toast_toggle"})
keyboard_settings_donator.add_line()
keyboard_settings_donator.add_button('Вернуться в Прочее',
                                     payload={"type": "navigation",
                                              "place": "other"})
keyboard_settings_donator.add_button('Вернуться в начало',
                                     payload={"type": "navigation",
                                              "place": "main"})

# КЛАВИАТУРЫ ШИЗЫ
# начальная клавиатура настроек (обычные БД)
keyboard_shiza_moderator = VkKeyboard(one_time=False, inline=True)
keyboard_shiza_moderator.add_button(label='Просмотр БД', payload={"type": "shiza_action", "command": "watch_databases"},
                                    color=VkKeyboardColor.POSITIVE)
keyboard_shiza_moderator.add_line()
keyboard_shiza_moderator.add_button(label='Редактирование БД',
                                    payload={"type": "shiza_action", "command": "edit_databases"},
                                    color=VkKeyboardColor.NEGATIVE)
keyboard_shiza_moderator.add_line()
keyboard_shiza_moderator.add_button(label='Добавить модератора',
                                    payload={"type": "shiza_action", "command": "add_moderator"},
                                    color=VkKeyboardColor.POSITIVE)
keyboard_shiza_moderator.add_line()
keyboard_shiza_moderator.add_button(label='Добавить методички',
                                    payload={"type": "shiza_navigation", "place": "add_preset_books_info"},
                                    color=VkKeyboardColor.POSITIVE)
keyboard_shiza_moderator.add_line()
keyboard_shiza_moderator.add_button(label='Конец работы',
                                    payload={"type": "shiza_navigation", "place": "end_databases"},
                                    color=VkKeyboardColor.POSITIVE)

# начальная клавиатура настроек (Админская)
keyboard_shiza_admin = VkKeyboard(one_time=False, inline=True)
keyboard_shiza_admin.add_button(label='Просмотр БД', payload={"type": "shiza_action", "command": "watch_databases"},
                                color=VkKeyboardColor.POSITIVE)
keyboard_shiza_admin.add_line()
keyboard_shiza_admin.add_button(label='Редактирование БД',
                                payload={"type": "shiza_action", "command": "edit_databases"},
                                color=VkKeyboardColor.NEGATIVE)
keyboard_shiza_admin.add_line()
keyboard_shiza_admin.add_button(label='Парсинг всех БД',
                                payload={"type": "shiza_action", "command": "parse_all_databases"},
                                color=VkKeyboardColor.NEGATIVE)
keyboard_shiza_admin.add_line()
keyboard_shiza_admin.add_button(label='Добавить модератора',
                                payload={"type": "shiza_action", "command": "add_moderator"},
                                color=VkKeyboardColor.POSITIVE)
keyboard_shiza_admin.add_line()
keyboard_shiza_admin.add_button(label='Добавить донатера', payload={"type": "shiza_action", "command": "add_donator"},
                                color=VkKeyboardColor.POSITIVE)
keyboard_shiza_admin.add_line()
keyboard_shiza_admin.add_button(label='Конец работы', payload={"type": "shiza_navigation", "place": "end_databases"},
                                color=VkKeyboardColor.POSITIVE)

# клавиатура запуска бот_longpoll для добавления почты
keyboard_email = VkKeyboard(one_time=False, inline=True)
keyboard_email.add_button(label='Внести данные', payload={"type": "shiza_action", "command": "edit_email"},
                          color=VkKeyboardColor.NEGATIVE)
keyboard_email.add_line()
keyboard_email.add_button(label='Удалить данные', payload={"type": "shiza_action", "command": "delete_email"},
                          color=VkKeyboardColor.NEGATIVE)
keyboard_email.add_line()
keyboard_email.add_button(label='В начало', payload={"type": "shiza_navigation", "place": "start_databases"},
                          color=VkKeyboardColor.POSITIVE)
keyboard_email.add_line()
keyboard_email.add_button(label='Конец работы', payload={"type": "shiza_navigation", "place": "end_databases"},
                          color=VkKeyboardColor.POSITIVE)

# клавиатура запуска бот_longpoll для добавления календаря
keyboard_gcal = VkKeyboard(one_time=False, inline=True)
keyboard_gcal.add_button(label='Внести данные', payload={"type": "shiza_action", "command": "edit_calendar"},
                         color=VkKeyboardColor.NEGATIVE)
keyboard_gcal.add_line()
keyboard_gcal.add_button(label='Удалить данные', payload={"type": "shiza_action", "command": "delete_calendar"},
                         color=VkKeyboardColor.NEGATIVE)
keyboard_gcal.add_line()
keyboard_gcal.add_button(label='В начало', payload={"type": "shiza_navigation", "place": "start_databases"},
                         color=VkKeyboardColor.POSITIVE)
keyboard_gcal.add_line()
keyboard_gcal.add_button(label='Конец работы', payload={"type": "shiza_navigation", "place": "end_databases"},
                         color=VkKeyboardColor.POSITIVE)

# клавиатура запуска бот_longpoll для добавления почты и календаря
keyboard_books = VkKeyboard(one_time=False, inline=True)
keyboard_books.add_button(label='Установить по умолчанию',
                          payload={"type": "shiza_action", "command": "add_preset_books"},
                          color=VkKeyboardColor.NEGATIVE)
keyboard_books.add_line()
keyboard_books.add_button(label='В начало', payload={"type": "shiza_navigation", "place": "start_databases"},
                          color=VkKeyboardColor.POSITIVE)
keyboard_books.add_line()
keyboard_books.add_button(label='Конец работы', payload={"type": "shiza_navigation", "place": "end_databases"},
                          color=VkKeyboardColor.POSITIVE)

# клавиатура выхода на главную шизы
keyboard_end = VkKeyboard(one_time=False, inline=True)
keyboard_end.add_button(label='В начало', payload={"type": "shiza_navigation", "place": "start_databases"},
                        color=VkKeyboardColor.POSITIVE)

'''    
keyboard = VkKeyboard(one_time=False, inline=True)
keyboard.add_button(label='В начало', color=VkKeyboardColor.PRIMARY, payload={"type": "shiza_navigation", "place": "start_databases"})
keyboard.add_button(label='Конец работы', color=VkKeyboardColor.NEGATIVE, payload={"type": "shiza_navigation", "place": "end_databases"})
'''

# ЗАПИСЬ КЛАВИАТУР
# ГЛАВНЫЕ
with open('keyboard_main.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_main.get_keyboard())

with open('keyboard_main_mail.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_main_mail.get_keyboard())

with open('keyboard_main_cal.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_main_cal.get_keyboard())

with open('keyboard_main_mail_cal.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_main_mail_cal.get_keyboard())

# ВЛОЖЕННЫЕ
with open('keyboard_table_study.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_table_study.get_keyboard())

with open('keyboard_table_exam.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_table_exam.get_keyboard())

with open('keyboard_table_mixed.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_table_mixed.get_keyboard())

with open('keyboard_table_.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_table_.get_keyboard())

with open('kb_table_other_even.json', 'w', encoding='utf-8') as f:
    f.write(kb_table_other_even.get_keyboard())

with open('kb_table_other_odd.json', 'w', encoding='utf-8') as f:
    f.write(kb_table_other_odd.get_keyboard())

with open('keyboard_calendar.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_calendar.get_keyboard())

with open('keyboard_other.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_other.get_keyboard())

# настройки
with open('keyboard_settings_admin.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_settings_admin.get_keyboard())

with open('keyboard_settings_moderator.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_settings_moderator.get_keyboard())

with open('keyboard_settings_user.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_settings_user.get_keyboard())

with open('keyboard_settings_donator.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_settings_donator.get_keyboard())

with open('keyboard_table_settings.json', 'w', encoding='utf-8') as f:
    f.write(kb_table_settings.get_keyboard())

with open('keyboard_table_settings_type.json', 'w', encoding='utf-8') as f:
    f.write(kb_table_settings_type.get_keyboard())

# ШИЗА
with open('keyboard_change_group.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_change_group.get_keyboard())

with open('false_command_keyboard.json', 'w', encoding='utf-8') as f:
    f.write(false_command_keyboard.get_keyboard())

with open('keyboard_shiza_moderator.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_shiza_moderator.get_keyboard())

with open('keyboard_shiza_admin.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_shiza_admin.get_keyboard())

with open('keyboard_email.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_email.get_keyboard())

with open('keyboard_gcal.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_gcal.get_keyboard())

with open('keyboard_books.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_books.get_keyboard())

with open('keyboard_end.json', 'w', encoding='utf-8') as f:
    f.write(keyboard_end.get_keyboard())
