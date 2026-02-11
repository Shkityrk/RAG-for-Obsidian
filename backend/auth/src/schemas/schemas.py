from pydantic import BaseModel, EmailStr
from typing import Optional

__all__ = [
    "UserLogin",
    "UserBase",
    "UserOut",
    "UserCreate"
]


class UserBase(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    user_role: str = "client"


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    password: str
    user_role: Optional[str] = "client"


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(UserBase):
    id: int

    class Config:
        orm_mode = True
