# dependencies: []
"""
Парсинг анекдотов с анекдот.ру в txt-шки - архивный скрипт на всякий случай
"""

import logging
import time
import sys
sys.setrecursionlimit(10**8)
import requests
from bs4 import BeautifulSoup

logging.basicConfig(filename='base/log.log', level=logging.DEBUG, format='%(asctime)s %(message)s')

file = open('base/count.txt', 'r')
count = int(file.readlines()[-1])
file.close()

def get_anekdot(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'lxml')
    musor = soup.find('div', 'col-left col-left-margin').find_all('div', class_='topicbox')

    new_musor = []

    for i in range(len(musor) - 1):
        if musor[i + 1].find('div', class_='text') is not None:
            new_musor.append(musor[i + 1].find('div', class_='text').text)
    return new_musor


def save_anekdot(number, text):
    file = open('base/' + str(number) + '.txt', 'w')
    file.write(text)
    file.close()
    return 0

def main(k):
    global count
    anekdots = get_anekdot(url='https://www.anekdot.ru/random/anekdot/')
    for i in range(len(anekdots)):
        save_anekdot(k+i, anekdots[i])
        count = k+i
    time.sleep(0.2)
    print('Текущий: ' + count)
    main(k+20)

def try_main():
    try:
        main(count)
    except:
        try_main()

try_main()