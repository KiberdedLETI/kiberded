# dependencies: [chat_bot]
import json
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

"""
Здесь находится код для генерации всех клавиатур, общих для пользователей бота
"""

# ГЛАВНЫЕ КЛАВИАТУРЫ
# Основная клавиатура с календарем и почтой
kb_main_mail_cal = VkKeyboard(one_time=False)
kb_main_mail_cal.add_button('Расписание', color=VkKeyboardColor.POSITIVE,
                            payload={"type": "navigation",
                                     "place": "table"})
kb_main_mail_cal.add_button('Календарь', color=VkKeyboardColor.POSITIVE,
                            payload={"type": "navigation",
                                     "place": "calendar"})  # или это пихнуть в расписание
kb_main_mail_cal.add_line()
kb_main_mail_cal.add_button('Методички', color=VkKeyboardColor.PRIMARY,
                            payload={"type": "navigation",
                                     "place": "books"})
kb_main_mail_cal.add_button('Преподы', color=VkKeyboardColor.PRIMARY,
                            payload={"type": "navigation",
                                     "place": "prepods"})

kb_main_mail_cal.add_line()
kb_main_mail_cal.add_openlink_button('Личный кабинет', link='https://lk.etu.ru')
kb_main_mail_cal.add_openlink_button('Почта группы', link='mail_url_placeholder')
kb_main_mail_cal.add_line()
kb_main_mail_cal.add_button('Прочее', color=VkKeyboardColor.NEGATIVE,
                            payload={"type": "navigation",
                                     "place": "other"})
kb_main_mail_cal.add_openlink_button('Мудл', link='https://vec.etu.ru')

# Основная клавиатура без календаря и с почтой
kb_main_mail = VkKeyboard(one_time=False)
kb_main_mail.add_button('Расписание', color=VkKeyboardColor.POSITIVE,
                        payload={"type": "navigation",
                                 "place": "table"})
kb_main_mail.add_line()
kb_main_mail.add_button('Методички', color=VkKeyboardColor.PRIMARY,
                        payload={"type": "navigation",
                                 "place": "books"})
kb_main_mail.add_button('Преподы', color=VkKeyboardColor.PRIMARY,
                        payload={"type": "navigation",
                                 "place": "prepods"})
kb_main_mail.add_line()
kb_main_mail.add_openlink_button('Личный кабинет', link='https://lk.etu.ru')
kb_main_mail.add_openlink_button('Почта группы', link='mail_url_placeholder')
kb_main_mail.add_line()
kb_main_mail.add_button('Прочее', color=VkKeyboardColor.NEGATIVE,
                        payload={"type": "navigation",
                                 "place": "other"})
kb_main_mail.add_openlink_button('Мудл', link='https://vec.etu.ru')

# Основная клавиатура без почты с календарем
kb_main_cal = VkKeyboard(one_time=False)
kb_main_cal.add_button('Расписание', color=VkKeyboardColor.POSITIVE,
                       payload={"type": "navigation",
                                "place": "table"})
kb_main_cal.add_button('Календарь', color=VkKeyboardColor.POSITIVE,
                       payload={"type": "navigation",
                                "place": "calendar"})
kb_main_cal.add_line()
kb_main_cal.add_button('Методички', color=VkKeyboardColor.PRIMARY,
                       payload={"type": "navigation",
                                "place": "books"})
kb_main_cal.add_button('Преподы', color=VkKeyboardColor.PRIMARY,
                       payload={"type": "navigation",
                                "place": "prepods"})
kb_main_cal.add_line()
kb_main_cal.add_openlink_button('Личный кабинет', link='https://lk.etu.ru')
kb_main_cal.add_openlink_button('Мудл', link='https://vec.etu.ru')
kb_main_cal.add_line()
kb_main_cal.add_button('Прочее', color=VkKeyboardColor.NEGATIVE,
                       payload={"type": "navigation",
                                "place": "other"})

# Основная клавиатура без почты и календаря
kb_main = VkKeyboard(one_time=False)
kb_main.add_button('Расписание', color=VkKeyboardColor.POSITIVE,
                   payload={"type": "navigation",
                            "place": "table"})
kb_main.add_line()
kb_main.add_button('Методички', color=VkKeyboardColor.PRIMARY,
                   payload={"type": "navigation",
                            "place": "books"})
kb_main.add_button('Преподы', color=VkKeyboardColor.PRIMARY,
                   payload={"type": "navigation",
                            "place": "prepods"})

kb_main.add_line()
kb_main.add_openlink_button('Личный кабинет', link='https://lk.etu.ru')
kb_main.add_openlink_button('Мудл', link='https://vec.etu.ru')
kb_main.add_line()
kb_main.add_button('Прочее', color=VkKeyboardColor.NEGATIVE,
                   payload={"type": "navigation",
                            "place": "other"})

# ВЛОЖЕННЫЕ КЛАВИАТУРЫ
# Клавиатура "Расписания" пустая
kb_table_ = VkKeyboard(one_time=False)
kb_table_.add_button('Где расписание?', color=VkKeyboardColor.NEGATIVE,
                     payload={"type": "action",
                              "action_type": "message",
                              "command": "table_empty"})
kb_table_.add_line()
kb_table_.add_button('Вернуться в начало',
                     payload={"type": "navigation",
                              "place": "main"})

# Клавиатура "Расписания" пустая если есть доп. группа. Аналогично, если нет основного расписания - не показываем ничего
kb_table__additional = VkKeyboard(one_time=False)
kb_table__additional.add_button('Где расписание?', color=VkKeyboardColor.NEGATIVE,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_empty"})
kb_table__additional.add_line()
kb_table__additional.add_button('Вернуться в начало',
                                payload={"type": "navigation",
                                         "place": "main"})

# Клавиатура "Расписания" СЕССИЯ
kb_table_exam = VkKeyboard(one_time=False)
kb_table_exam.add_button('Расписание экзаменов', color=VkKeyboardColor.NEGATIVE,
                         payload={"type": "action",
                                  "action_type": "message",
                                  "command": "table_exam"})
kb_table_exam.add_line()
kb_table_exam.add_button('Вернуться в начало',
                         payload={"type": "navigation",
                                  "place": "main"})

# Клавиатура "Расписания" обычная
kb_table_study = VkKeyboard(one_time=False)
kb_table_study.add_button('Расписание на сегодня', color=VkKeyboardColor.PRIMARY,
                          payload={"type": "action",
                                   "action_type": "message",
                                   "command": "table_today"})
kb_table_study.add_line()
kb_table_study.add_button('Расписание на завтра', color=VkKeyboardColor.SECONDARY,
                          payload={"type": "action",
                                   "action_type": "message",
                                   "command": "table_tomorrow"})
kb_table_study.add_line()
kb_table_study.add_button('На другие дни', color=VkKeyboardColor.NEGATIVE,
                          payload={"type": "navigation",
                                   "place": "table_other"})
kb_table_study.add_line()
kb_table_study.add_button('Вернуться в начало',
                          payload={"type": "navigation",
                                   "place": "main"})

# Клавиатура "Расписания" смешанная (экзамены + расписание)
kb_table_mixed = VkKeyboard(one_time=False)
kb_table_mixed.add_button('Расписание экзаменов', color=VkKeyboardColor.NEGATIVE,
                          payload={"type": "action",
                                   "action_type": "message",
                                   "command": "table_exam"})
kb_table_mixed.add_line()
kb_table_mixed.add_button('Расписание на сегодня', color=VkKeyboardColor.PRIMARY,
                          payload={"type": "action",
                                   "action_type": "message",
                                   "command": "table_today"})
kb_table_mixed.add_line()
kb_table_mixed.add_button('Расписание на завтра', color=VkKeyboardColor.SECONDARY,
                          payload={"type": "action",
                                   "action_type": "message",
                                   "command": "table_tomorrow"})
kb_table_mixed.add_line()
kb_table_mixed.add_button('На другие дни', color=VkKeyboardColor.NEGATIVE,
                          payload={"type": "navigation",
                                   "place": "table_other"})
kb_table_mixed.add_line()
kb_table_mixed.add_button('Вернуться в начало',
                          payload={"type": "navigation",
                                   "place": "main"})

# Аналогичные клавиатуры с доп.группой
# Клавиатура "Расписания" СЕССИЯ
kb_table_exam_additional = VkKeyboard(one_time=False)
kb_table_exam_additional.add_button('Экзамены', color=VkKeyboardColor.NEGATIVE,
                                    payload={"type": "action",
                                             "action_type": "message",
                                             "command": "table_exam"})
kb_table_exam_additional.add_line()
kb_table_exam_additional.add_button('Экзамены (доп)', color=VkKeyboardColor.NEGATIVE,
                                    payload={"type": "action",
                                             "action_type": "message",
                                             "command": "table_exam_2"})
kb_table_exam_additional.add_line()
kb_table_exam_additional.add_button('Вернуться в начало',
                                    payload={"type": "navigation",
                                             "place": "main"})

# Клавиатура "Расписания" обычная
kb_table_study_additional = VkKeyboard(one_time=False)
kb_table_study_additional.add_button('Сегодня', color=VkKeyboardColor.PRIMARY,
                                     payload={"type": "action",
                                              "action_type": "message",
                                              "command": "table_today"})
kb_table_study_additional.add_button('Сегодня (доп)', color=VkKeyboardColor.PRIMARY,
                                     payload={"type": "action",
                                              "action_type": "message",
                                              "command": "table_today_2"})
kb_table_study_additional.add_line()
kb_table_study_additional.add_button('Завтра', color=VkKeyboardColor.SECONDARY,
                                     payload={"type": "action",
                                              "action_type": "message",
                                              "command": "table_tomorrow"})
kb_table_study_additional.add_button('Завтра (доп)', color=VkKeyboardColor.SECONDARY,
                                     payload={"type": "action",
                                              "action_type": "message",
                                              "command": "table_tomorrow_2"})
kb_table_study_additional.add_line()
kb_table_study_additional.add_button('Всё', color=VkKeyboardColor.NEGATIVE,
                                     payload={"type": "navigation",
                                              "place": "table_other"})
kb_table_study_additional.add_button('Всё (доп)', color=VkKeyboardColor.NEGATIVE,
                                     payload={"type": "navigation",
                                              "place": "table_other_2"})
kb_table_study_additional.add_line()
kb_table_study_additional.add_button('Вернуться в начало',
                                     payload={"type": "navigation",
                                              "place": "main"})

# Клавиатура "Расписания" смешанная (экзамены + расписание)
kb_table_mixed_additional = VkKeyboard(one_time=False)
kb_table_mixed_additional.add_button('Экзамены', color=VkKeyboardColor.NEGATIVE,
                                     payload={"type": "action",
                                              "action_type": "message",
                                              "command": "table_exam"})
kb_table_mixed_additional.add_button('Экзамены (доп)', color=VkKeyboardColor.NEGATIVE,
                                     payload={"type": "action",
                                              "action_type": "message",
                                              "command": "table_exam_2"})
kb_table_mixed_additional.add_line()
kb_table_mixed_additional.add_button('Сегодня', color=VkKeyboardColor.PRIMARY,
                                     payload={"type": "action",
                                              "action_type": "message",
                                              "command": "table_today"})
kb_table_mixed_additional.add_button('Сегодня (доп)', color=VkKeyboardColor.PRIMARY,
                                     payload={"type": "action",
                                              "action_type": "message",
                                              "command": "table_today_2"})
kb_table_mixed_additional.add_line()
kb_table_mixed_additional.add_button('Завтра', color=VkKeyboardColor.SECONDARY,
                                     payload={"type": "action",
                                              "action_type": "message",
                                              "command": "table_tomorrow"})
kb_table_mixed_additional.add_button('Завтра (доп)', color=VkKeyboardColor.SECONDARY,
                                     payload={"type": "action",
                                              "action_type": "message",
                                              "command": "table_tomorrow_2"})
kb_table_mixed_additional.add_line()
kb_table_mixed_additional.add_button('Всё', color=VkKeyboardColor.NEGATIVE,
                                     payload={"type": "navigation",
                                              "place": "table_other"})
kb_table_mixed_additional.add_button('Всё (доп)', color=VkKeyboardColor.NEGATIVE,
                                     payload={"type": "navigation",
                                              "place": "table_other_2"})
kb_table_mixed_additional.add_line()
kb_table_mixed_additional.add_button('Вернуться в начало',
                                     payload={"type": "navigation",
                                              "place": "main"})

# Клавиатура "Календарь"
kb_calendar = VkKeyboard(one_time=False)
kb_calendar.add_button('Календарь на сегодня', color=VkKeyboardColor.POSITIVE,
                       payload={"type": "action",
                                "action_type": "message",
                                "command": "calendar_today"})
kb_calendar.add_line()
kb_calendar.add_button('Календарь на завтра', color=VkKeyboardColor.POSITIVE,
                       payload={"type": "action",
                                "action_type": "message",
                                "command": "calendar_tomorrow"})
kb_calendar.add_line()
kb_calendar.add_button('Вернуться в начало',
                       payload={"type": "navigation",
                                "place": "main"})

# Клавиатура "Прочее"
kb_other = VkKeyboard(one_time=False)
kb_other.add_button('Случайный анекдот', color=VkKeyboardColor.POSITIVE,
                    payload={"type": "action",
                             "action_type": "message",
                             "command": "random_anecdote"})
kb_other.add_button('Случайный тост', color=VkKeyboardColor.POSITIVE,
                    payload={"type": "action",
                             "action_type": "message",
                             "command": "random_toast"})
kb_other.add_line()
kb_other.add_button('Подписаться на Анекдот', color=VkKeyboardColor.SECONDARY,
                    payload={"type": "action",
                             "action_type": "message",
                             "command": "anecdote_subscribe"})
kb_other.add_button('Отписаться от Анекдота', color=VkKeyboardColor.SECONDARY,
                    payload={"type": "action",
                             "action_type": "message",
                             "command": "anecdote_unsubscribe"})
kb_other.add_line()
kb_other.add_button('Рассылка Расписания', color=VkKeyboardColor.PRIMARY,
                    payload={"type": "navigation",
                             "place": "kb_table_settings_sub"})
kb_other.add_line()
kb_other.add_button('Настройки', color=VkKeyboardColor.NEGATIVE,
                    payload={"type": "navigation",
                             "place": "settings"})
kb_other.add_button('Telegram', color=VkKeyboardColor.PRIMARY,
                    payload={"type": "action",
                             "action_type": "message",
                             "command": "link_tg"})
kb_other.add_line()
kb_other.add_button('Поддержать проект', color=VkKeyboardColor.POSITIVE,
                    payload={"type": "navigation",
                             "place": "donate"})
kb_other.add_line()
kb_other.add_button('Вернуться в начало',
                    payload={"type": "navigation",
                             "place": "main"})

# Клавиатура "Настройки рассылки расписания"; кнопки - тип, время, отписаться, назад
kb_table_settings = VkKeyboard(one_time=False)
kb_table_settings.add_button('Тип', color=VkKeyboardColor.PRIMARY,
                             payload={"type": "navigation",
                                      "place": "table_settings_type"})
kb_table_settings.add_line()
kb_table_settings.add_button('Время', color=VkKeyboardColor.PRIMARY,
                             payload={"type": "action",
                                      "action_type": "shiza",
                                      "target": "table_settings_time"})
kb_table_settings.add_line()
kb_table_settings.add_button('Отписаться', color=VkKeyboardColor.NEGATIVE,
                             payload={"type": "navigation",
                                      "place": "kb_table_settings_unsub"})
kb_table_settings.add_line()
kb_table_settings.add_button('Назад', color=VkKeyboardColor.SECONDARY,
                             payload={"type": "navigation",
                                      "place": "other"})

# Клавиатура "Настройки типа рассылки расписания"; кнопки - ежедневно, еженедельно, обе, назад
kb_table_settings_type = VkKeyboard(one_time=False)
kb_table_settings_type.add_button('Ежедневно', color=VkKeyboardColor.PRIMARY,
                                  payload={"type": "action",
                                           "action_type": "message",
                                           "command": "table_set_type",
                                           "arg": "daily"})
kb_table_settings_type.add_line()
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
                                           "arg": "both"})
kb_table_settings_type.add_line()
kb_table_settings_type.add_button('Назад', color=VkKeyboardColor.NEGATIVE,
                                  payload={"type": "navigation",
                                           "place": "kb_table_settings"})

# Клавиатура "Настройки типа рассылки расписания" С КАЛЕНДАРЕМ; кнопки - ежедневно, еженедельно, обе, назад
kb_table_settings_type_cal = VkKeyboard(one_time=False)
kb_table_settings_type_cal.add_button('Календарь', color=VkKeyboardColor.PRIMARY,
                                      payload={"type": "action",
                                               "action_type": "message",
                                               "command": "table_set_type",
                                               "arg": "calendar"})
kb_table_settings_type_cal.add_line()
kb_table_settings_type_cal.add_button('Ежедневно', color=VkKeyboardColor.PRIMARY,
                                      payload={"type": "action",
                                               "action_type": "message",
                                               "command": "table_set_type",
                                               "arg": "daily"})
kb_table_settings_type_cal.add_line()
kb_table_settings_type_cal.add_button('Еженедельно', color=VkKeyboardColor.PRIMARY,
                                      payload={"type": "action",
                                               "action_type": "message",
                                               "command": "table_set_type",
                                               "arg": "weekly"})
kb_table_settings_type_cal.add_line()
kb_table_settings_type_cal.add_button('Оба', color=VkKeyboardColor.PRIMARY,
                                      payload={"type": "action",
                                               "action_type": "message",
                                               "command": "table_set_type",
                                               "arg": "both"})
kb_table_settings_type_cal.add_line()
kb_table_settings_type_cal.add_button('Назад', color=VkKeyboardColor.NEGATIVE,
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

# Аналогичные клавиатуры расписания по неделям, но для доп. группы пользователя
# Четная неделя - "главная"
kb_table_other_even_2 = VkKeyboard(one_time=False)
kb_table_other_even_2.add_button('Понедельник (чёт)', color=VkKeyboardColor.PRIMARY,
                                 payload={"type": "action",
                                          "action_type": "message",
                                          "command": "table_weekday_2",
                                          "weekday": "Понедельник (чёт)"})
kb_table_other_even_2.add_button('Понедельник (нечёт)', color=VkKeyboardColor.SECONDARY,
                                 payload={"type": "action",
                                          "action_type": "message",
                                          "command": "table_weekday_2",
                                          "weekday": "Понедельник (нечёт)"})
kb_table_other_even_2.add_line()
kb_table_other_even_2.add_button('Вторник (чёт)', color=VkKeyboardColor.PRIMARY,
                                 payload={"type": "action",
                                          "action_type": "message",
                                          "command": "table_weekday_2",
                                          "weekday": "Вторник (чёт)"})
kb_table_other_even_2.add_button('Вторник (нечёт)', color=VkKeyboardColor.SECONDARY,
                                 payload={"type": "action",
                                          "action_type": "message",
                                          "command": "table_weekday_2",
                                          "weekday": "Вторник (нечёт)"})
kb_table_other_even_2.add_line()
kb_table_other_even_2.add_button('Среда (чёт)', color=VkKeyboardColor.PRIMARY,
                                 payload={"type": "action",
                                          "action_type": "message",
                                          "command": "table_weekday_2",
                                          "weekday": "Среда (чёт)"})
kb_table_other_even_2.add_button('Среда (нечёт)', color=VkKeyboardColor.SECONDARY,
                                 payload={"type": "action",
                                          "action_type": "message",
                                          "command": "table_weekday_2",
                                          "weekday": "Среда (нечёт)"})
kb_table_other_even_2.add_line()
kb_table_other_even_2.add_button('Четверг (чёт)', color=VkKeyboardColor.PRIMARY,
                                 payload={"type": "action",
                                          "action_type": "message",
                                          "command": "table_weekday_2",
                                          "weekday": "Четверг (чёт)"})
kb_table_other_even_2.add_button('Четверг (нечёт)', color=VkKeyboardColor.SECONDARY,
                                 payload={"type": "action",
                                          "action_type": "message",
                                          "command": "table_weekday_2",
                                          "weekday": "Четверг (нечёт)"})
kb_table_other_even_2.add_line()
kb_table_other_even_2.add_button('Пятница (чёт)', color=VkKeyboardColor.PRIMARY,
                                 payload={"type": "action",
                                          "action_type": "message",
                                          "command": "table_weekday_2",
                                          "weekday": "Пятница (чёт)"})
kb_table_other_even_2.add_button('Пятница (нечёт)', color=VkKeyboardColor.SECONDARY,
                                 payload={"type": "action",
                                          "action_type": "message",
                                          "command": "table_weekday_2",
                                          "weekday": "Пятница (нечёт)"})
kb_table_other_even_2.add_line()
kb_table_other_even_2.add_button('Суббота (чёт)', color=VkKeyboardColor.PRIMARY,
                                 payload={"type": "action",
                                          "action_type": "message",
                                          "command": "table_weekday_2",
                                          "weekday": "Суббота (чёт)"})
kb_table_other_even_2.add_button('Суббота (нечёт)', color=VkKeyboardColor.SECONDARY,
                                 payload={"type": "action",
                                          "action_type": "message",
                                          "command": "table_weekday_2",
                                          "weekday": "Суббота (нечёт)"})
kb_table_other_even_2.add_line()
kb_table_other_even_2.add_button('Вернуться в расписания', color=VkKeyboardColor.POSITIVE,
                                 payload={"type": "navigation",
                                          "place": "table"})
kb_table_other_even_2.add_button('Вернуться в начало',
                                 payload={"type": "navigation",
                                          "place": "main"})

# нечетная неделя - "главная"
kb_table_other_odd_2 = VkKeyboard(one_time=False)
kb_table_other_odd_2.add_button('Понедельник (чёт)', color=VkKeyboardColor.SECONDARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_weekday_2",
                                         "weekday": "Понедельник (чёт)"})
kb_table_other_odd_2.add_button('Понедельник (нечёт)', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_weekday_2",
                                         "weekday": "Понедельник (нечёт)"})
kb_table_other_odd_2.add_line()
kb_table_other_odd_2.add_button('Вторник (чёт)', color=VkKeyboardColor.SECONDARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_weekday_2",
                                         "weekday": "Вторник (чёт)"})
kb_table_other_odd_2.add_button('Вторник (нечёт)', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_weekday_2",
                                         "weekday": "Вторник (нечёт)"})
kb_table_other_odd_2.add_line()
kb_table_other_odd_2.add_button('Среда (чёт)', color=VkKeyboardColor.SECONDARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_weekday_2",
                                         "weekday": "Среда (чёт)"})
kb_table_other_odd_2.add_button('Среда (нечёт)', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_weekday_2",
                                         "weekday": "Среда (нечёт)"})
kb_table_other_odd_2.add_line()
kb_table_other_odd_2.add_button('Четверг (чёт)', color=VkKeyboardColor.SECONDARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_weekday_2",
                                         "weekday": "Четверг (чёт)"})
kb_table_other_odd_2.add_button('Четверг (нечёт)', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_weekday_2",
                                         "weekday": "Четверг (нечёт)"})
kb_table_other_odd_2.add_line()
kb_table_other_odd_2.add_button('Пятница (чёт)', color=VkKeyboardColor.SECONDARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_weekday_2",
                                         "weekday": "Пятница (чёт)"})
kb_table_other_odd_2.add_button('Пятница (нечёт)', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_weekday_2",
                                         "weekday": "Пятница (нечёт)"})
kb_table_other_odd_2.add_line()
kb_table_other_odd_2.add_button('Суббота (чёт)', color=VkKeyboardColor.SECONDARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_weekday_2",
                                         "weekday": "Суббота (чёт)"})
kb_table_other_odd_2.add_button('Суббота (нечёт)', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "action",
                                         "action_type": "message",
                                         "command": "table_weekday_2",
                                         "weekday": "Суббота (нечёт)"})
kb_table_other_odd_2.add_line()
kb_table_other_odd_2.add_button('Вернуться в расписания', color=VkKeyboardColor.POSITIVE,
                                payload={"type": "navigation",
                                         "place": "table"})
kb_table_other_odd_2.add_button('Вернуться в начало',
                                payload={"type": "navigation",
                                         "place": "main"})

# КЛАВИАТУРЫ НАСТРОЕК

# мини-клавиатура для настройки уведомлений о неизвестной команде, для всех пользователей
false_command_kb = VkKeyboard(one_time=False, inline=True)
false_command_kb.add_button(label='Ясно, не показывать это', color=VkKeyboardColor.POSITIVE,
                            payload={"type": "action", "action_type": "message",
                                     "command": "remove_notifications"})

# Клавиатура смены группы при ошибке группы
kb_change_group = VkKeyboard(one_time=False, inline=True)
kb_change_group.add_button(label='Изменить группу', color=VkKeyboardColor.POSITIVE,
                           payload={"type": "action",
                                    "action_type": "shiza",
                                    "target": "change_group"})

# Клавиатура настроек для адимнов
kb_settings_admin = VkKeyboard(one_time=False)
kb_settings_admin.add_button('Изменить доп. группу', color=VkKeyboardColor.PRIMARY,
                             payload={"type": "action",
                                      "action_type": "shiza",
                                      "target": "change_additional_group"})
kb_settings_admin.add_line()
kb_settings_admin.add_button('Работа с БД', color=VkKeyboardColor.PRIMARY,
                             payload={"type": "action",
                                      "action_type": "shiza",
                                      "target": "edit_database"})
kb_settings_admin.add_button('Работа с админскими БД', color=VkKeyboardColor.NEGATIVE,
                             payload={"type": "action",
                                      "action_type": "shiza",
                                      "target": "edit_admin_database"})
kb_settings_admin.add_line()
kb_settings_admin.add_button('Вернуться в Прочее',
                             payload={"type": "navigation",
                                      "place": "other"})
kb_settings_admin.add_button('Вернуться в начало',
                             payload={"type": "navigation",
                                      "place": "main"})

# Клавиатура настроек для модеров
kb_settings_moderator = VkKeyboard(one_time=False)
kb_settings_moderator.add_button('Изменить доп. группу', color=VkKeyboardColor.PRIMARY,
                                 payload={"type": "action",
                                          "action_type": "shiza",
                                          "target": "change_additional_group"})
kb_settings_moderator.add_line()
kb_settings_moderator.add_button('Работа с БД', color=VkKeyboardColor.PRIMARY,
                                 payload={"type": "action",
                                          "action_type": "shiza",
                                          "target": "edit_database"})
kb_settings_moderator.add_line()
kb_settings_moderator.add_button('Добавление в чат', color=VkKeyboardColor.SECONDARY,
                                 payload={"type": "action",
                                          "action_type": "message",
                                          "command": "add_chat"})
kb_settings_moderator.add_line()
kb_settings_moderator.add_button('Вернуться в Прочее',
                                 payload={"type": "navigation",
                                          "place": "other"})
kb_settings_moderator.add_button('Вернуться в начало',
                                 payload={"type": "navigation",
                                          "place": "main"})

# клавиатура настроек (смена группы) для обычных пользователей
kb_settings_user = VkKeyboard(one_time=False)
kb_settings_user.add_button('Изменить группу', color=VkKeyboardColor.PRIMARY,
                            payload={"type": "action",
                                     "action_type": "shiza",
                                     "target": "change_group"})
kb_settings_user.add_line()
kb_settings_user.add_button('Изменить доп. группу', color=VkKeyboardColor.PRIMARY,
                            payload={"type": "action",
                                     "action_type": "shiza",
                                     "target": "change_additional_group"})
kb_settings_user.add_line()
kb_settings_user.add_button('Добавление в чат', color=VkKeyboardColor.SECONDARY,
                            payload={"type": "action",
                                     "action_type": "message",
                                     "command": "add_chat"})
kb_settings_user.add_line()
kb_settings_user.add_button('Вернуться в Прочее',
                            payload={"type": "navigation",
                                     "place": "other"})
kb_settings_user.add_button('Вернуться в начало',
                            payload={"type": "navigation",
                                     "place": "main"})

# клавиатура настроек премиум-функций - пока это день дня и тосты
kb_settings_donator = VkKeyboard(one_time=False)
kb_settings_donator.add_button('Ежедневная пикча', color=VkKeyboardColor.POSITIVE,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": "day_of_day_toggle"})
kb_settings_donator.add_line()
kb_settings_donator.add_button('Еженедельный тост', color=VkKeyboardColor.POSITIVE,
                               payload={"type": "action",
                                        "action_type": "message",
                                        "command": "weekly_toast_toggle"})
kb_settings_donator.add_line()
kb_settings_donator.add_button('Вернуться в Прочее',
                               payload={"type": "navigation",
                                        "place": "other"})
kb_settings_donator.add_button('Вернуться в начало',
                               payload={"type": "navigation",
                                        "place": "main"})

# КЛАВИАТУРЫ ШИЗЫ
# начальная клавиатура настроек (обычные БД)
kb_shiza_moderator = VkKeyboard(one_time=False, inline=True)
kb_shiza_moderator.add_button(label='Просмотр БД', payload={"type": "shiza_action", "command": "watch_databases"},
                              color=VkKeyboardColor.POSITIVE)
kb_shiza_moderator.add_line()
kb_shiza_moderator.add_button(label='Редактирование БД',
                              payload={"type": "shiza_action", "command": "edit_databases"},
                              color=VkKeyboardColor.NEGATIVE)
kb_shiza_moderator.add_line()
kb_shiza_moderator.add_button(label='Добавить модератора',
                              payload={"type": "shiza_action", "command": "add_moderator"},
                              color=VkKeyboardColor.POSITIVE)
kb_shiza_moderator.add_line()
kb_shiza_moderator.add_button(label='Добавить методички',
                              payload={"type": "shiza_navigation", "place": "add_preset_books_info"},
                              color=VkKeyboardColor.POSITIVE)
kb_shiza_moderator.add_line()
kb_shiza_moderator.add_button(label='Конец работы',
                              payload={"type": "shiza_navigation", "place": "end_databases"},
                              color=VkKeyboardColor.POSITIVE)

# начальная клавиатура настроек (Админская)
kb_shiza_admin = VkKeyboard(one_time=False, inline=True)
kb_shiza_admin.add_button(label='Просмотр БД', payload={"type": "shiza_action", "command": "watch_databases"},
                          color=VkKeyboardColor.POSITIVE)
kb_shiza_admin.add_line()
kb_shiza_admin.add_button(label='Редактирование БД',
                          payload={"type": "shiza_action", "command": "edit_databases"},
                          color=VkKeyboardColor.NEGATIVE)
kb_shiza_admin.add_line()
kb_shiza_admin.add_button(label='Парсинг всех БД',
                          payload={"type": "shiza_action", "command": "parse_all_databases"},
                          color=VkKeyboardColor.NEGATIVE)
kb_shiza_admin.add_line()
kb_shiza_admin.add_button(label='Добавить модератора',
                          payload={"type": "shiza_action", "command": "add_moderator"},
                          color=VkKeyboardColor.POSITIVE)
kb_shiza_admin.add_line()
kb_shiza_admin.add_button(label='Добавить донатера', payload={"type": "shiza_action", "command": "add_donator"},
                          color=VkKeyboardColor.POSITIVE)
kb_shiza_admin.add_line()
kb_shiza_admin.add_button(label='Конец работы', payload={"type": "shiza_navigation", "place": "end_databases"},
                          color=VkKeyboardColor.POSITIVE)

# клавиатура запуска бот_longpoll для добавления почты
kb_email = VkKeyboard(one_time=False, inline=True)
kb_email.add_button(label='Внести данные', payload={"type": "shiza_action", "command": "edit_email"},
                    color=VkKeyboardColor.NEGATIVE)
kb_email.add_line()
kb_email.add_button(label='Удалить данные', payload={"type": "shiza_action", "command": "delete_email"},
                    color=VkKeyboardColor.NEGATIVE)
kb_email.add_line()
kb_email.add_button(label='В начало', payload={"type": "shiza_navigation", "place": "start_databases"},
                    color=VkKeyboardColor.POSITIVE)
kb_email.add_line()
kb_email.add_button(label='Конец работы', payload={"type": "shiza_navigation", "place": "end_databases"},
                    color=VkKeyboardColor.POSITIVE)

# клавиатура запуска бот_longpoll для добавления календаря
kb_gcal = VkKeyboard(one_time=False, inline=True)
kb_gcal.add_button(label='Внести данные', payload={"type": "shiza_action", "command": "edit_calendar"},
                   color=VkKeyboardColor.NEGATIVE)
kb_gcal.add_line()
kb_gcal.add_button(label='Удалить данные', payload={"type": "shiza_action", "command": "delete_calendar"},
                   color=VkKeyboardColor.NEGATIVE)
kb_gcal.add_line()
kb_gcal.add_button(label='В начало', payload={"type": "shiza_navigation", "place": "start_databases"},
                   color=VkKeyboardColor.POSITIVE)
kb_gcal.add_line()
kb_gcal.add_button(label='Конец работы', payload={"type": "shiza_navigation", "place": "end_databases"},
                   color=VkKeyboardColor.POSITIVE)

# клавиатура запуска бот_longpoll для добавления почты и календаря
kb_books = VkKeyboard(one_time=False, inline=True)
kb_books.add_button(label='Установить по умолчанию',
                    payload={"type": "shiza_action", "command": "add_preset_books"},
                    color=VkKeyboardColor.NEGATIVE)
kb_books.add_line()
kb_books.add_button(label='В начало', payload={"type": "shiza_navigation", "place": "start_databases"},
                    color=VkKeyboardColor.POSITIVE)
kb_books.add_line()
kb_books.add_button(label='Конец работы', payload={"type": "shiza_navigation", "place": "end_databases"},
                    color=VkKeyboardColor.POSITIVE)

# клавиатура выхода на главную шизы
kb_end = VkKeyboard(one_time=False, inline=True)
kb_end.add_button(label='В начало', payload={"type": "shiza_navigation", "place": "start_databases"},
                  color=VkKeyboardColor.POSITIVE)

'''    
keyboard = VkKeyboard(one_time=False, inline=True)
keyboard.add_button(label='В начало', color=VkKeyboardColor.PRIMARY, payload={"type": "shiza_navigation", "place": "start_databases"})
keyboard.add_button(label='Конец работы', color=VkKeyboardColor.NEGATIVE, payload={"type": "shiza_navigation", "place": "end_databases"})
'''

# ЗАПИСЬ КЛАВИАТУР
kbs = ["kb_main",
       "kb_main_mail",
       "kb_main_cal",
       "kb_main_mail_cal",
       "kb_table_study",
       "kb_table_study_additional",
       "kb_table_exam",
       "kb_table_exam_additional",
       "kb_table_mixed",
       "kb_table_mixed_additional",
       "kb_table_",
       "kb_table__additional",
       "kb_table_other_even",
       "kb_table_other_even_2",
       "kb_table_other_odd",
       "kb_table_other_odd_2",
       "kb_calendar",
       "kb_other",
       "kb_settings_admin",
       "kb_settings_moderator",
       "kb_settings_user",
       "kb_settings_donator",
       "kb_table_settings",
       "kb_table_settings_type",
       "kb_table_settings_type_cal",
       "kb_change_group",
       "false_command_kb",
       "kb_shiza_moderator",
       "kb_shiza_admin",
       "kb_email",
       "kb_gcal",
       "kb_books",
       "kb_end"]

print("Генерация общих клавиатур ВКонтакте...")
for k in kbs:
    print(k)
    with open(f'{k}.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(json.loads(eval(k).get_keyboard()), ensure_ascii=False, indent=4))
print("Готово!")
