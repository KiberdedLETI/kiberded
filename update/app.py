"""
Сервис для обработки webhooks c github и для работы с базами данных/серверными функциями.
Бывший "обновляющий дед"
"""
import random
import subprocess
import traceback

from fastapi import Depends, FastAPI, Request, HTTPException, Header
from fastapi.responses import RedirectResponse
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.staticfiles import StaticFiles

from db import User, create_db_and_tables, get_async_session
from schemas import UserRead, UserUpdate
from users import current_user, fastapi_users, cookie_auth_backend

from fastapi.templating import Jinja2Templates

import logging
from bot_functions import send_telegram_message, get_acme_flag, get_path
from users_function import create_user
from pydantic import BaseModel
import os
import sys
sys.path.insert(0, '../')
from deds_schemas import main as get_all_dependencies
import sqlite3

logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)


app = FastAPI(docs_url=None)
app.add_middleware(HTTPSRedirectMiddleware)  # переадресация на https


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
            return templates.TemplateResponse("admin_panel.html", {"request": request, "user": user})
        if is_verified:
            return templates.TemplateResponse("moderator_panel.html", {"request": request, "user": user})
        else:
            return templates.TemplateResponse("unverified.html", {"request": request, "user": user})
    else:
        return RedirectResponse("/login", status_code=302)


@app.get("/panel")
async def panel(request: Request, user: User = Depends(current_user)):
    if user:
        is_verified = user.is_verified
        is_superuser = user.is_superuser
        if is_superuser:
            return templates.TemplateResponse("admin_panel.html", {"request": request, "user": user})
        if is_verified:
            return templates.TemplateResponse("moderator_panel.html", {"request": request, "user": user})
        else:
            return templates.TemplateResponse("unverified.html", {"request": request, "user": user})
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
            response = {"request": request,
                        "user": user}

            with sqlite3.connect(f'{get_path()}databases/{user.group}.db') as con:
                cur = con.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type ='table' AND name NOT LIKE 'sqlite_%'")
                tables = [e[0] for e in cur.fetchall()]
                for table in tables:
                    cur.execute(f"PRAGMA table_info({table})")
                    response[f"{table}_columns"] = cur.fetchall()
                    cur.execute(f"SELECT * FROM {table}")
                    response[table] = cur.fetchall()

            return templates.TemplateResponse("database.html", response)
        else:
            return {"detail": "403 Forbidden"}


@app.get("/backups")
async def backups(request: Request, user: User = Depends(current_user)):
    if not user:
        return RedirectResponse("/login", status_code=302)
    else:
        is_verified = user.is_verified
        if is_verified:
            with sqlite3.connect(f'{get_path()}admindb/backups.db') as con:
                cur = con.cursor()
                cur.execute("SELECT * FROM backups")
                all_backups = cur.fetchall()
            return templates.TemplateResponse("backups.html", {"request": request,
                                                               "user": user,
                                                               "years": ['2022', '2023'],
                                                                "backups": all_backups},)
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
            return templates.TemplateResponse("databases_all.html", {"request": request, "user": user})
        else:
            return {"detail": "403 Forbidden"}


@app.get("/users_moderation")
async def users_moderation(request: Request, user: User = Depends(current_user),
                           session: AsyncSession = Depends(get_async_session), id: str = ''):
    if not user:
        return RedirectResponse("/login", status_code=302)
    else:
        if user.is_superuser:
            statement = select(User)
            result = await session.execute(statement)
            all_users = result.scalars().all()
            try:
                result = await session.execute(statement.where(User.id == id))
                edit_user = result.scalars().all()
            except Exception:
                id = ''
                edit_user = ['']
            if not edit_user:
                id = ''
                edit_user = ['']
            return templates.TemplateResponse("users_moderation.html",
                                                  {"request": request,
                                                   "user": user,
                                                   "users": all_users,
                                                   "id": id,
                                                   "edit_user": edit_user[0]})
        else:
            return {"detail": "403 Forbidden"}


@app.get("/change_password")
async def change_password(request: Request, user: User = Depends(current_user), token: str = ''):
    if token:
        return templates.TemplateResponse("change_password.html", {"request": request, "user": user, "token": token})
    else:
        return RedirectResponse("/generate_password_token", status_code=302)


@app.get("/generate_password_token")
async def generate_password_token(request: Request, user: User = Depends(current_user)):
    if not user:
        return RedirectResponse("/login", status_code=302)
    else:
        return templates.TemplateResponse("generate_password_token.html", {"request": request, "user": user, "email": user.email})


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
async def verify_user(request: Request, token='', user: User = Depends(current_user)):
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("verify.html", {"request": request, "user": user, "token": token})


@app.get("/getFileFromTelegram")
async def download_file_from_telegram(request: Request, file_id='', backup=False, user: User = Depends(current_user)):
    if not user:
        return RedirectResponse("/login", status_code=302)
    else:
        if user.is_superuser:
            return templates.TemplateResponse("download_file_from_telegram.html", {"request": request, "user": user})
        else:
            return {"detail": "403 Forbidden"}


async def get_webhook_info(x_github_event: str, payload):
    """
    Обработка вебхуков с возвратом сообщения для оповещений.
    Немного boilerplate, но это заготовка под более подробные логи, если они понадобятся
    """

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
        return message, None

    elif x_github_event == 'push':
        pusher_name = payload['pusher']['name']
        repository_full_name = payload['repository']['full_name']
        commits = payload['commits']
        message = f'[github] Пользователь {pusher_name} сделал push репозитория {repository_full_name}\n\n'

        global_added = set()
        global_removed = set()
        global_modified = set()

        for commit in commits:
            commit_author_name = commit['author']['name']
            commit_message = commit['message']

            global_added.update(commit['added'])
            global_removed.update(commit['removed'])
            global_modified.update(commit['modified'])

            message += f'\t{commit_author_name}: {commit_message}\n\n'

        if global_added:
            message += f'Список добавленных файлов:\n'
            message += '\n'.join(list(set(global_added)))

        if global_removed:
            message += f'Список удаленных файлов:\n'
            message += '\n'.join(list(set(global_removed)))

        if global_modified:
            message += f'Список модифицированных файлов:\n'
            message += '\n'.join(list(set(global_modified)))

        reboot_deds = {}
        if repository_full_name == 'KiberdedLETI/kiberded':
            all_dependencies = get_all_dependencies()
            for file in global_added.union(global_removed, global_modified):
                try:
                    dependence = all_dependencies[file]
                except Exception as e:
                    message += f'\nПроизошла ошибка при обработке зависимостей: {str(e)}. Перезагружаем всех дедов.\n'
                    dependence = {'chat_bot': True,
                                  'telegram_bot': True,
                                  'scheduler': True,
                                  'watcher': True,
                                  'mail_bot': True,
                                  'update_daemon': True}
                for dep in dependence:
                    reboot_deds[dep] = True

        reboot_deds = list(reboot_deds.keys())
        if 'update_daemon' in reboot_deds:  # сам себя должен перезагружать последним
            index_update_daemon = reboot_deds.index('update_daemon')
            reboot_deds.pop(index_update_daemon)
            reboot_deds.append('update_daemon')
        if reboot_deds:
            message += f'\n\nНужно перезагрузить дедов:\n'
            for ded in reboot_deds:
                message += f'{ded}\n'
        return message, reboot_deds

    elif x_github_event == 'commit_comment':
        message = f'[github] Кто-то прокомментировал коммент'
        return message, None
    elif x_github_event == 'create':
        message = f'[github] Кто-то создал репозиторий'
        return message, None
    elif x_github_event == 'delete':
        message = f'[github] Кто-то удалил репозиторий'
        return message, None
    elif x_github_event == 'discussion':
        message = f'[github] Кто-то сделал что-то с дискуссиями'
        return message, None
    elif x_github_event == 'discussion_comment':
        message = f'[github] Кто-то прокомментировал дискуссии'
        return message, None
    elif x_github_event == 'fork':
        message = f'[github] Кто-то что-то сделал с форком'
        return message, None
    elif x_github_event == 'issue_comment':
        message = f'[github] Кто-то прокомментировал issue'
        return message, None
    elif x_github_event == 'issues':
        message = f'[github] Кто-то что-то сделал с issue'
        return message, None
    elif x_github_event == 'member':
        message = f'[github] Кто-то что-то сделал с members'
        return message, None
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
        return message, None
    elif x_github_event == 'organization':
        message = f'[github] Кто-то что-то сделал с организацией'
        return message, None
    elif x_github_event == 'pull_request':
        message = f'[github] Кто-то сделал что-то с pull request'
        return message, None
    elif x_github_event == 'pull_request_review':
        message = f'[github] Кто-то сделал что-то с pull request'
        return message, None
    elif x_github_event == 'pull_request_review_comment':
        message = f'[github] Кто-то сделал что-то с pull request'
        return message, None
    elif x_github_event == 'pull_request_review_thread':
        message = f'[github] Кто-то сделал что-то с pull request'
        return message, None
    elif x_github_event == 'repository':
        message = f'[github] Кто-то сделал что-то глобальное с репозиторием'
        return message, None
    else:
        return '', None


@app.post("/webhook")
async def webhook(request: Request,  x_github_event: str = Header(...),):
    payload = await request.json()
    try:
        if x_github_event == 'push':
            result = subprocess.run(['/bin/bash', '/root/kiberded/server/update.sh'], stdout=subprocess.PIPE)
            message, reboot_deds = await get_webhook_info(x_github_event, payload)
            send_telegram_message(message)
            # send_telegram_message(f'Репозиторий обновлен, перезагрузка дедов...')
            for ded in reboot_deds:
                os.system(f'systemctl restart {ded}')
        return {'message': 'ok'}
    except Exception as e:
        message = f'[github] Произошла ошибка при парсинге webhook: \n{traceback.format_exc()}\n\npayload: {payload}'
        send_telegram_message(message)


@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()
    send_telegram_message(f'Веб-обновляющий дед активирован')

