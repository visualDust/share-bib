from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, StringConstraints

Username = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$",
    ),
]
NewPassword = Annotated[str, StringConstraints(min_length=8, max_length=256)]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


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
    new_password: NewPassword


class AdminUserCreate(BaseModel):
    username: Username
    password: NewPassword
    email: EmailStr | None = None
    display_name: DisplayName | None = None


class AdminPasswordReset(BaseModel):
    new_password: NewPassword


class AdminUserUpdate(BaseModel):
    username: Username | None = None
    email: EmailStr | None = None
    display_name: DisplayName | None = None


class AdminDeleteUser(BaseModel):
    mode: Literal["transfer", "delete"] = "delete"
    transfer_to: str | None = None  # target user_id when mode=transfer


class AdminUserOut(BaseModel):
    id: str
    username: str
    email: str | None = None
    display_name: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
