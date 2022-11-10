"""
Сервис для обработки webhooks c github и для работы с базами данных/серверными функциями.
Бывший "обновляющий дед"
"""
import random
from typing import Optional, Union

from fastapi import Depends, FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.staticfiles import StaticFiles

from db import User, create_db_and_tables, get_async_session
from schemas import UserCreate, UserRead, UserUpdate
from users import current_user, fastapi_users, cookie_auth_backend

from fastapi.templating import Jinja2Templates

import toml
import logging
import sys
from telebot.async_telebot import AsyncTeleBot
from bot_functions import send_telegram_message
from users_function import create_user
from pydantic import BaseModel

logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)


app = FastAPI()


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


@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()
