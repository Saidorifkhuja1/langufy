from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


# User Role Enum
class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"
    SUPERUSER = "superuser"


class UserBase(BaseModel):
    email: EmailStr
    user_name: str = Field(..., min_length=3, max_length=50)
    full_name: str
    phone_number: str
    role: UserRole = UserRole.STUDENT

    @validator('user_name')
    def validate_username(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, underscores and hyphens')
        return v.lower()


class UserAuth(BaseModel):
    email: EmailStr
    password: str


class UserPassword(BaseModel):
    old_password: str
    new_password: str


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: UUID
    is_active: str  # 'active' or 'inactive'
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True