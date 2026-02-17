from datetime import datetime

from pydantic import BaseModel


class UserOut(BaseModel):
    id: str
    username: str
    email: str | None = None
    display_name: str | None = None
    is_active: bool
    is_admin: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class UserBrief(BaseModel):
    user_id: str
    username: str
    display_name: str | None = None


class ChangePassword(BaseModel):
    old_password: str
    new_password: str


class AdminUserCreate(BaseModel):
    username: str
    password: str
    email: str | None = None
    display_name: str | None = None


class AdminPasswordReset(BaseModel):
    new_password: str


class AdminUserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    display_name: str | None = None


class AdminDeleteUser(BaseModel):
    mode: str = "delete"  # "transfer" or "delete"
    transfer_to: str | None = None  # target user_id when mode=transfer


class AdminUserOut(BaseModel):
    id: str
    username: str
    email: str | None = None
    display_name: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
