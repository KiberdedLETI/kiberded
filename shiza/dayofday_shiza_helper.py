"""
Скрипт для обновления картинок днядня в длюдеде, нужен скорее для ручного редкого использования и истории, так что
нужно вручную вписывать логин и пароль
"""
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
import json
import sqlite3
import os
import requests
import toml
import sys
import logging

path = f'{os.path.abspath(os.curdir)}/'
logger = logging.getLogger('chat_bot')

try:
    config = toml.load('./configuration.toml')  # если импортируется из корня
except FileNotFoundError:
    try:
        config = toml.load('../configuration.toml')  # если импортируется из папки server
    except FileNotFoundError:
        print('configuration.toml не найден!')
        sys.exit()

token = config.get('Kiberded').get('token')


# обновлялка базы /admindb/databases/day_of_day.db
def dayofday_db_updater():
    try:
        login, password = '+', ''  # логин и пароль от длюдеды, необходимо прописать вручную
        vk_session = vk_api.VkApi(login, password)
        vk_session.auth()
        response = vk_session.method('photos.get', {'owner_id': 648179760, 'album_id': 280009249, 'count': 1000})
        items = json.loads(json.dumps(response.get('items')))
        message = 'Запущено обнолвение базы с фотками'
        os.system(f'python3 {path}send2debug.py {message}')  # запуск скрипта для отправки сообщения в конфу
        con = sqlite3.connect(f'{path}admindb/databases/day_of_day.db')
        cur = con.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS count(count_field INTEGER)''')
        cur.execute('''DELETE FROM count''')
        cur.execute('''INSERT INTO count VALUES (?)''', [str(len(items))])
        cur.execute('''CREATE TABLE IF NOT EXISTS photos(link text)''')
        cur.execute('''DELETE FROM photos''')
        for item in items:
            url = f'photo{item.get("owner_id")}_{item.get("id")}'
            cur.execute('''INSERT INTO photos VALUES (?)''', [str(url)])
        os.system(f'python3 {path}send2debug.py База фоточек обновлена. Фоток на данный момент: {str(len(items))}')
        con.commit()
        con.close()
        return 'все чики-пуки :))'

    except vk_api.AuthError as error_msg:
        os.system(
            f'python3 {path}send2debug.py Произошла ошибка при авторизации страницы для деда, функция обновления dayofday базы')
        return
    except sqlite3.Error as sqlite3_error:
        con.close()  # todo это надо?
        os.system(
            f'python3 {path}send2debug.py Произошла sqlite-ошибка в функции обновления dayofday базы : {str(sqlite3_error)}')
        return
    except Exception as e:
        os.system(
            f'python3 {path}send2debug.py Произошла общая ошибка в функции обновления dayofday базы: {str(e)}')
        return


def predlozhka_func(event):
    message_dump = json.dumps(event.obj.message)
    message = json.loads(message_dump)
    if message.get('attachments'):
        attachments_dump = json.dumps(message.get('attachments'))
        attachments = json.loads(attachments_dump)
        if attachments[0].get('type') == 'photo':
            # все чики-пуки, товарищ действительно прислал фотку, чекаем первую фотку:
            photo = json.loads(json.dumps(attachments[0].get('photo')))
            sizes = photo.get('sizes')
            summ_resolution = 0
            i = 0  # элемент списка с наибольшим разрешеним
            for k in range(len(sizes)):
                if sizes[k].get('height') + sizes[k].get('width') > summ_resolution:
                    summ_resolution = sizes[k].get('height') + sizes[k].get('width')
                    i = k
            url = sizes[i].get('url')
            return url, photo, f'Пикча принята: {url}'
        else:
            # отправляем его к лешему
            return 0, 0, 'Ошибка. Предложка закрыта.'
    else:
        # отправка сообщения об отсутствии вложения
        return 0, 0, 'А где фотка? Прелдожка закрыта.'


def golosovanie_keyboard(randint):  # создание клавиатуры голосования
    keyboard_golosovanie = VkKeyboard(one_time=False, inline=True)
    keyboard_golosovanie.add_callback_button('Сойдет', color=VkKeyboardColor.POSITIVE, payload={"button": f"golos",
                                                                                                "id": f"{randint}",
                                                                                                "is_positive": 1})
    keyboard_golosovanie.add_callback_button('Херня полная', color=VkKeyboardColor.NEGATIVE,
                                             payload={"button": f"golos",
                                                      "id": f"{randint}",
                                                      "is_positive": 0})
    return keyboard_golosovanie.get_keyboard()


def download_photo(url, name):  # загружает фотку в cache/name.jpg
    r = requests.get(url)
    with open(f"{path}cache/{name}.jpg", "wb") as code:
        code.write(r.content)
    return 0


def add_photo(id, master):  # добавляет фото №id в альбом, master - айди предложившего
    try:
        login, password = '', ''  # логин и пароль длюдеды, необходимо прописать вручную
        vk_session = vk_api.VkApi(login, password)  # сессия страницыдлюдеды
        vk_session.auth()

        vk_session_bot = vk_api.VkApi(token=token)  # сессия основного деда
        vk_bot = vk_session_bot.get_api()
        vk_bot.messages.send(random_id=get_random_id(), chat_id=1,
                             message=f'Кажется, меня вызвали добавить фотку номер {id}')
        upload = vk_api.VkUpload(vk_session)
        photo_file = upload.photo(photos=f'{path}cache/{id}.jpg', album_id=280009249)
        print(photo_file)
        vk_bot.messages.send(random_id=get_random_id(), chat_id=1,
            message=f'Фотка добавлена: https://vk.com/photo648179760_{photo_file[0]["id"]}')
    except vk_api.AuthError:
        os.system(
            f'python3 {path}send2debug.py Произошла ошибка при авторизации страницы для деда, '
            f'функция обновления dayofday базы')
        return