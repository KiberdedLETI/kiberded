#! /usr/bin/env python
# -*- coding: utf-8 -*-
# dependencies: [chat_bot, telegram_bot]

import random
import bs4
import requests
from bs4 import BeautifulSoup


def get_random_anekdot(url='https://www.anekdot.ru/random/anekdot/'):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html5lib')
    musor = soup.find('div', 'col-left col-left-margin').find_all('div', class_='topicbox')

    new_musor = []

    for i in range(len(musor) - 1):
        if musor[i + 1].find('div', class_='text') is not None:
            new_musor.append(musor[i + 1].find('div', class_='text').text)
    ans = str(new_musor[random.randint(0, len(new_musor)-1)])
    if not ans:  # если пустой анекдот
        return 'Произошла ошибка, попробуй еще раз'
    return ans


def get_random_toast(header=True):
    """
    Получение рандомного тоста.
    :param header: if True - добавляет 'Случайный тост с сайта rzhunemogu.ru\n'
    :return:
    """

    toast = 'Случайный тост с сайта rzhunemogu.ru\n' if header else ''

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
    }
    url = "http://rzhunemogu.ru/Widzh/Tost.aspx"
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html5lib')
    musor = soup.find('span').contents

    for string in musor:
        if type(string) is bs4.element.NavigableString:
            toast = toast + str(string) + '\n'
    return toast
