from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    full_name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class AdminUserCreate(BaseModel):
    full_name: str
    email: str
    password: str
    role: str = "technician"
    customer_id: Optional[int] = None


class UserCustomerLink(BaseModel):
    customer_id: int


class UserRoleUpdate(BaseModel):
    role: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    customer_id: Optional[int]
    is_active: int
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str