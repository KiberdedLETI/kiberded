import uuid
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    JWTStrategy,
    CookieTransport
)
from fastapi_users.db import SQLAlchemyUserDatabase

from db import User, get_user_db
from bot_functions import send_telegram_message, get_web_secret

SECRET = get_web_secret()


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        telegram_id = user.telegram_username
        vk_id = user.vk_username
        id_text = ''

        if vk_id != '':
            id_text += f'vk_id: https://vk.com/id{vk_id}\n'
        if telegram_id != '':
            id_text += f'telegram_id: {telegram_id}\n'
        if vk_id == '' and telegram_id == '':
            id_text += f'ВНИМАНИЕ! что-то пошло не по плану, и пользователю не присвоены идентификаторы в соц.сетях'
        message = f'[web] Зарегистрирован пользователь {user.username} из группы {user.group}\n{id_text}'
        send_telegram_message(message)

    async def on_after_forgot_password(self, user: User, token: str, request: Optional[Request] = None):
        print(token)

        if user.telegram_username:  # todo https и поправить текст в принципе
            message = f'Кто-то запросил восстановление пароля твоей учетной записи на сайте. Если это был ты, ' \
                      f'перейди по ссылке:\nhttp://evgen.tk:8000/change_password?token={token}'
            send_telegram_message(message, user.telegram_username)
            send_telegram_message(f'[web] Пользователь {user.username} запросил восстановление пароля')

    async def on_after_reset_password(self, user: User, request: Optional[Request] = None):
        send_telegram_message(f'[web] Пользователь {user.username} из группы {user.group} изменил пароль')

    async def on_after_request_verify(self, user: User, token: str, request: Optional[Request] = None):
        send_telegram_message(f'[web] Пользователю {user.username} из группы {user.group} нужна аудиенция: \n'
                              f'https://kiberded.ga/verify?token={token}')

    async def on_after_verify(self, user: User, request: Optional[Request] = None):
        send_telegram_message(f'[web] Пользователь {user.username} из группы {user.group} успешно верифицирован.')

    async def on_after_delete(self, user: User, request: Optional[Request] = None):
        send_telegram_message(f'[web] Пользователь {user.username} из группы {user.group} был удален.')


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)


cookie_transport = CookieTransport(cookie_max_age=86400, cookie_secure=False)

cookie_auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [cookie_auth_backend],
)

current_user = fastapi_users.current_user(optional=True)
current_active_user = fastapi_users.current_user(active=True)
