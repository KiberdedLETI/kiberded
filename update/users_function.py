"""
Файл для регистрации пользователей
"""
import contextlib
import traceback
from typing import Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_async_session, get_user_db, User
from schemas import UserCreate
from users import get_user_manager
from fastapi_users.exceptions import UserAlreadyExists

from bot_functions import send_telegram_message, send_vk_message

get_async_session_context = contextlib.asynccontextmanager(get_async_session)
get_user_db_context = contextlib.asynccontextmanager(get_user_db)
get_user_manager_context = contextlib.asynccontextmanager(get_user_manager)


async def create_user(username: str, password: str, group: str, telegram_username: str = '',
                      vk_username: str = '', is_superuser: bool = False):
    try:
        if vk_username == '' and telegram_username == '':
            send_telegram_message(f'[web]Пользователь {username} из группы {group} не создан: не указан vk/tg айди.')
        async with get_async_session_context() as session:
            async with get_user_db_context(session) as user_db:
                async with get_user_manager_context(user_db) as user_manager:
                    email = f'{username}@example.com'
                    user = await user_manager.create(
                        UserCreate(
                            email=email, password=password, username=username, group=group,
                            telegram_username=telegram_username, vk_username=vk_username, is_superuser=is_superuser
                        )
                    )
                    message_user = f'Ты был зарегистрирован на сайте https://kiberded.ga как модератор.\n' \
                                   f'Логин: {username}, пароль: {password}. ' \
                                   f'Пароль можно поменять, зайдя в личный кабинет'
                    if telegram_username != '':
                        try:
                            send_telegram_message(message_user, telegram_username)
                        except Exception as e:
                            message = f'[web] Не удалось отправить сообщение о регистрации пользователю в тг: \n' \
                                      f'id = {telegram_username}, traceback: {str(e)}\n{traceback.format_exc()}'
                            send_telegram_message(message)
                    if vk_username != '':
                        try:
                            send_vk_message(message_user, int(vk_username))
                        except Exception as e:
                            message = f'[web] Не удалось отправить сообщение о регистрации пользователю в вк: \n' \
                                      f'id = {vk_username}, traceback: {str(e)}\n{traceback.format_exc()}'
                            send_telegram_message(message)
    except UserAlreadyExists:
        send_telegram_message(f'[web] Пользователь {username} из группы {group} не создан: уже существует.')


if __name__ == "__main__":
    import asyncio
    asyncio.run(create_user('test', 'this_is_test_password', '9281', vk_username='71982805', is_superuser=True))