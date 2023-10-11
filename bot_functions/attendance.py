# dependencies: [telegram_bot, scheduler]
"""
Скрипт для работы с "ИС Посещаемость" (простигосподи) и, возможно, с ЛК
"""

import json
import requests
from bs4 import BeautifulSoup
import time


def start_new_session() -> requests.session:
    """
    Создание новой сессии. Функция чисто для того, чтобы не городить этот огород в других скриптах.

    :return requests.session: сессия
    """

    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'}
    session = requests.session()
    session.headers = headers

    return session


def auth_in_lk(session, email, password) -> tuple:
    """
    Авторизация в ЛК в рамках текущей сессии.
    Признак успешной авторизации, насколько я понял - наличие полей XSRF-TOKEN и lk_etu_ru_session в cookies.

    :param requests.session session: текущая сессия (requests.session())
    :param str email: email, он же логин от ЛК
    :param str password: пароль от ЛК
    :return tuple: кортеж из кода статуса запроса и сессии: [code, session]
    """
    url_login = 'https://lk.etu.ru/login'
    data = session.get(url_login)

    soup = BeautifulSoup(data.text, "html.parser")
    token = soup.find('input', {'name': '_token'}).attrs['value']
    datapost = {'_token': token,
                'email': email,
                'password': password}
    data_ans = session.post(url_login, data=datapost)

    code = data_ans.status_code

    if code == 200 and data_ans.url == 'https://lk.etu.ru/login':  # в случае неверных учетных данных возвращается 200
        # и не проихсодит переадресации на https://lk.etu.ru/student
        code = 419
    return code, session


def auth_in_attendance(session) -> tuple:
    """
    Авторизация в ИС Посещаемость в рамках текущей сессии.
    Сессия должна быть уже залогинена в ЛК, либо в нее должны быть подгружены куки XSRF-TOKEN и lk_etu_ru_session.
    Признак успешной авторизации - поле connect.digital-attendance в cookies сессии.

    :param requests.session session: текущая сессия (requests.session())
    :return tuple: кортеж из кода статуса запроса и сессии: [code, session]
    """

    url_login = 'https://lk.etu.ru/oauth/authorize?response_type=code&redirect_uri=https%3A%2F%2Fdigital.etu.ru%2Fatt' \
                'endance%2Fapi%2Fauth%2Fredirect&client_id=29'  # ссылка может измениться, лучше брать ее непосредственно из лк
    data = session.get(url_login)
    soup = BeautifulSoup(data.text, "html.parser")
    token = soup.find('input', {'name': '_token'}).attrs['value']
    auth_token = soup.find('input', {'name': 'auth_token'}).attrs['value']
    state = soup.find('input', {'name': 'state'}).attrs['value']
    client_id = soup.find('input', {'name': 'client_id'}).attrs['value']

    datapost = {'_token': token,
                'auth_token': auth_token,
                'state': state,
                'client_id': client_id}

    data_ans = session.post('https://lk.etu.ru/oauth/authorize', data=datapost)

    code = data_ans.status_code
    return code, session


def get_info_from_attendance(session, all_data=False) -> tuple:
    """
    Получение инфы с портала: время (ну просто потому что могу), инфа о текущем юзере, пары за эту неделю и статистика
    посещений за все время (только если all_data = True)

    :param requests.session session: текущая сессия (requests.session())
    :return tuple: кортеж из кода статуса запроса инфы о парах и json-ответов:
    [code, time_data, user, checkin, alldata (if all_data, иначе пустой словарь)]
    """
    url_time = 'https://digital.etu.ru/attendance/api/settings/time'
    url_user = 'https://digital.etu.ru/attendance/api/auth/current-user'
    url_checkin = 'https://digital.etu.ru/attendance/api/schedule/check-in'
    url_all = 'https://digital.etu.ru/attendance/api/schedule/stats/student'

    time_data = session.get(url_time).json()
    user = session.get(url_user).json()

    data_checkin = session.get(url_checkin)
    code = data_checkin.status_code
    checkin = data_checkin.json()

    alldata = session.get(url_all).json() if all_data else {}
    return code, time_data, user, checkin, alldata


def check_in_at_lesson(session, id) -> tuple:
    """
    Отмечание на паре.
    :param requests.session session: текущая сессия (requests.session())
    :param id: id пары
    :return tuple: кортеж из кода статуса запроса инфы о парах и json-ответов:
    """
    url = f'https://digital.etu.ru/attendance/api/schedule/check-in/{id}'
    data_ans = session.post(url)
    code = data_ans.status_code
    return code, session
