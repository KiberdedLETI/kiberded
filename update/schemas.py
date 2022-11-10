import uuid
from typing import Optional

from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    username: str
    group: str
    telegram_username: Optional[str]
    vk_username: Optional[str]


class UserCreate(schemas.BaseUserCreate):
    username: str
    group: str
    telegram_username: Optional[str]
    vk_username: Optional[str]


class UserUpdate(schemas.BaseUserUpdate):
    username: str
    group: str
    telegram_username: Optional[str]
    vk_username: Optional[str]
