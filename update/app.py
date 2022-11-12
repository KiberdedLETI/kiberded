"""
Сервис для обработки webhooks c github и для работы с базами данных/серверными функциями.
Бывший "обновляющий дед"
"""
import random
import traceback

from fastapi import Depends, FastAPI, Request, HTTPException, Header
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.staticfiles import StaticFiles

from db import User, create_db_and_tables, get_async_session
from schemas import UserRead, UserUpdate
from users import current_user, fastapi_users, cookie_auth_backend

from fastapi.templating import Jinja2Templates

import logging
from bot_functions import send_telegram_message, get_acme_flag
from users_function import create_user
from pydantic import BaseModel
import os

logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)


app = FastAPI(docs_url=None)


class RegisterItem(BaseModel):
    username: str
    group: str
    telegram_username: str
    vk_username: str


app.include_router(
    fastapi_users.get_auth_router(cookie_auth_backend),
    prefix="/auth/cookie",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


templates = Jinja2Templates(directory="./templates")
app.mount("/public", StaticFiles(directory="public"), name="public")
if get_acme_flag():
    app.mount("/.well-known", StaticFiles(directory=".well-known"), name=".well-known")


@app.get("/")
async def root(request: Request, user: User = Depends(current_user)):
    if user:
        is_verified = user.is_verified
        is_superuser = user.is_superuser
        if is_superuser:
            return templates.TemplateResponse("admin_panel.html", {"request": request})
        if is_verified:
            return templates.TemplateResponse("moderator_panel.html", {"request": request})
        else:
            return templates.TemplateResponse("unverified.html", {"request": request})
    else:
        return RedirectResponse("/login", status_code=302)


@app.get("/panel")
async def panel(request: Request, user: User = Depends(current_user)):
    if user:
        is_verified = user.is_verified
        is_superuser = user.is_superuser
        if is_superuser:
            return templates.TemplateResponse("admin_panel.html", {"request": request})
        if is_verified:
            return templates.TemplateResponse("moderator_panel.html", {"request": request})
        else:
            return templates.TemplateResponse("unverified.html", {"request": request})
    else:
        return RedirectResponse("/login", status_code=302)


@app.get("/login")
async def login(request: Request, user: User = Depends(current_user)):
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})
    else:
        return RedirectResponse("/", status_code=302)


@app.get("/database")
async def database(request: Request, user: User = Depends(current_user)):
    if not user:
        return RedirectResponse("/login", status_code=302)
    else:
        is_verified = user.is_verified
        if is_verified:
            return templates.TemplateResponse("database.html", {"request": request})
        else:
            return {"detail": "403 Forbidden"}


@app.get("/stop_all")
async def stop_all(request: Request, user: User = Depends(current_user)):
    if not user:
        ip = request.client.host
        message = f'[web] Неизвестный с ip {ip} хотел остановить дедов'
        send_telegram_message(message)
        return RedirectResponse("/login", status_code=302)
    else:
        is_superuser = user.is_superuser
        if is_superuser:
            message = f'[web] Юзер {user.username} остановил дедов'
            send_telegram_message(message)
            # todo выполнение скрипта
            return templates.TemplateResponse("stop_all.html", {"request": request})
        else:
            message = f'[web] Плохиш {user.username} хотел перезагрузить дедов, но он не админ'
            send_telegram_message(message)
            return {"detail": "403 Forbidden"}


@app.get("/restart_all")
async def restart_all(request: Request, user: User = Depends(current_user)):
    if not user:
        ip = request.client.host
        message = f'[web] Неизвестный плохиш с ip {ip} хотел перезагрузить дедов'
        send_telegram_message(message)
        return RedirectResponse("/login", status_code=302)
    else:
        is_superuser = user.is_superuser
        if is_superuser:
            message = f'[web] Юзер {user.username} перезагрузил дедов'
            send_telegram_message(message)
            # todo выполнение скрипта
            return templates.TemplateResponse("restart_all.html", {"request": request})
        else:
            message = f'[web] Плохиш {user.username} хотел перезагрузить дедов, но он не админ'
            send_telegram_message(message)
            return {"detail": "403 Forbidden"}


@app.get("/databases_all")
async def databases_all(request: Request, user: User = Depends(current_user)):
    if not user:
        return RedirectResponse("/login", status_code=302)
    else:
        is_superuser = user.is_superuser
        if is_superuser:
            return templates.TemplateResponse("databases_all.html", {"request": request})
        else:
            return {"detail": "403 Forbidden"}


@app.get("/users_moderation")
async def users_moderation(request: Request, user: User = Depends(current_user), session: AsyncSession = Depends(get_async_session)):
    if not user:
        return RedirectResponse("/login", status_code=302)
    else:
        if user.is_superuser:
            statement = select(User)
            result = await session.execute(statement)
            all_users = result.scalars().all()
            return templates.TemplateResponse("users_moderation.html", {"request": request, "users": all_users})
        else:
            return {"detail": "403 Forbidden"}


@app.get("/change_password")
async def change_password(request: Request, user: User = Depends(current_user), token: str = ''):
    if token:
        return templates.TemplateResponse("change_password.html", {"request": request, "token": token})
    else:
        return RedirectResponse("/generate_password_token", status_code=302)


@app.get("/generate_password_token")
async def generate_password_token(request: Request, user: User = Depends(current_user)):
    if not user:
        return RedirectResponse("/login", status_code=302)
    else:
        return templates.TemplateResponse("generate_password_token.html", {"request": request, "email": user.email})


@app.post("/auth/register")
async def register_user(request: Request, user: User = Depends(current_user), item: RegisterItem = None):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f'403 Forbidden',
        )
    else:
        if user.is_superuser:
            if item:
                password = ''
                for i in range(10):
                    password += random.choice(list(
                        '1234567890abcdefghigklmnopqrstuvyxwzABCDEFGHIGKLMNOPQRSTUVYXWZ_*!<>{};'))
                await create_user(item.username, password, item.group, item.telegram_username, item.vk_username)
                raise HTTPException(status_code=status.HTTP_201_CREATED)

            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Data is empty')
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'403 Forbidden')


@app.get("/verify")
async def verify_user(request: Request, token=''):
    return templates.TemplateResponse("verify.html", {"request": request, "token": token})


async def get_webhook_info(x_github_event: str, payload):
    if x_github_event == 'ping':
        hook_type = payload['hook']['type']
        sender_login = payload['sender']['login']
        hook_config_url = payload['hook']['config']['url']

        if hook_type == 'Repository':
            repository_full_name = payload['repository']['full_name']
            message = f'[github] Пользователь {sender_login} создал новый webhook в репозитории ' \
                      f'{repository_full_name} на адрес {hook_config_url}'
        elif hook_type == 'Organization':
            organization_login = payload['organization']['login']
            message = f'[github] Пользователь {sender_login} создал новый webhook в организации ' \
                      f'{organization_login} на адрес {hook_config_url}'
        else:
            message = f'[github] Пользователь {sender_login} создал новый webhook на адрес {hook_config_url}' \
                      f'\nhook_type={hook_type}'
        return message

    elif x_github_event == 'push':
        pusher_name = payload['pusher']['name']
        repository_full_name = payload['repository']['full_name']
        commits = payload['commits']
        message = f'[github] Пользователь {pusher_name} сделал push репозитория {repository_full_name}\n\n'

        for commit in commits:
            commit_author_name = commit['author']['name']
            commit_message = commit['message']
            message += f'\t{commit_author_name}: {commit_message}\n\n'

        return message

    elif x_github_event == 'commit_comment':
        message = f'[github] Кто-то прокомментировал коммент'
        return message
    elif x_github_event == 'create':
        message = f'[github] Кто-то создал репозиторий'
        return message
    elif x_github_event == 'delete':
        message = f'[github] Кто-то удалил репозиторий'
        return message
    elif x_github_event == 'discussion':
        message = f'[github] Кто-то сделал что-то с дискуссиями'
        return message
    elif x_github_event == 'discussion_comment':
        message = f'[github] Кто-то прокомментировал дискуссии'
        return message
    elif x_github_event == 'fork':
        message = f'[github] Кто-то что-то сделал с форком'
        return message
    elif x_github_event == 'issue_comment':
        message = f'[github] Кто-то прокомментировал issue'
        return message
    elif x_github_event == 'issues':
        message = f'[github] Кто-то что-то сделал с issue'
        return message
    elif x_github_event == 'member':
        message = f'[github] Кто-то что-то сделал с memvers'
        return message
    elif x_github_event == 'meta':
        action = payload['action']
        hook_type = payload['hook']['type']
        sender_login = payload['sender']['login']
        hook_config_url = payload['hook']['config']['url']

        if hook_type == 'Repository':
            repository_full_name = payload['repository']['full_name']
            addition = f'в репозитории {repository_full_name}'
        elif hook_type == 'Organization':
            organization_login = payload['organization']['login']
            addition = f'в организации {organization_login}'
        else:
            addition = f'непонятно где'
        if action == 'deleted':
            message = f'[github] Пользователь {sender_login} удалил вебхук {addition} по адресу {hook_config_url}'
        else:
            message = f'[githib] Пользователь {sender_login} сделал что-то непонятное с вебхуком {addition} по ' \
                      f'адресу {hook_config_url}\npayload: {payload}'
        return message
    elif x_github_event == 'organization':
        message = f'[github] Кто-то что-то сделал с организацией'
        return message
    elif x_github_event == 'pull_request':
        message = f'[github] Кто-то сделал что-то с pull request'
        return message
    elif x_github_event == 'pull_request_review':
        message = f'[github] Кто-то сделал что-то с pull request'
        return message
    elif x_github_event == 'pull_request_review_comment':
        message = f'[github] Кто-то сделал что-то с pull request'
        return message
    elif x_github_event == 'pull_request_review_thread':
        message = f'[github] Кто-то сделал что-то с pull request'
        return message
    elif x_github_event == 'repository':
        message = f'[github] Кто-то сделал что-то глобальное с репозиторием'
        return message
    else:
        return ''


@app.post("/webhook")
async def webhook(request: Request,  x_github_event: str = Header(...),):
    payload = await request.json()
    try:
        message = await get_webhook_info(x_github_event, payload)
        if message == '':
            return {'detail': '400 BAD REQUEST'}
        else:
            send_telegram_message(message)
            return {'message': 'ok'}
    except Exception as e:
        message = f'[github] Произошла ошибка при парсинге webhook: \n{traceback.format_exc()}\n\npayload: {payload}'
        send_telegram_message(message)
    finally:
        if x_github_event == 'push':
            os.system('/bin/bash /root/kiberded/server/update.sh')


@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()
