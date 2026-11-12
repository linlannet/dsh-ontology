"""系统层出入参模型：字段与 Java DTO 对齐，输入兼容 camelCase 别名。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer


def _fmt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


class LoginIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_name: str = Field(alias="userName")
    password: str


class RegisterIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_name: str = Field(alias="userName")
    password: str
    nick_name: str | None = Field(default=None, alias="nickName")
    email: str | None = None
    phonenumber: str | None = None
    tenant_id: int | None = Field(default=None, alias="tenantId")


class LoginOut(BaseModel):
    token: str
    user_id: int
    user_name: str
    nick_name: str | None = None
    role_level: int
    tenant_id: int | None = None


class UserInfoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    tenant_id: int | None = None
    role_level: int
    user_name: str
    nick_name: str | None = None
    email: str | None = None
    phonenumber: str | None = None
    status: str | None = None
    login_ip: str | None = None
    login_date: datetime | None = None
    created_at: datetime | None = None
    remark: str | None = None

    @field_serializer("login_date", "created_at")
    def _serialize_dt(self, value: datetime | None) -> str | None:
        return _fmt(value)


class UserUpdateIn(BaseModel):
    nick_name: str | None = None
    email: str | None = None
    phonenumber: str | None = None
    status: str | None = None
    remark: str | None = None


class RoleIn(BaseModel):
    role_code: str | None = None
    role_name: str | None = None
    role_level: int | None = None
    description: str | None = None
    status: str | None = None
    remark: str | None = None


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_id: int
    role_code: str
    role_name: str
    role_level: int
    description: str | None = None
    status: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    remark: str | None = None

    @field_serializer("created_at", "updated_at")
    def _serialize_dt(self, value: datetime | None) -> str | None:
        return _fmt(value)


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: int
    user_id: int | None = None
    tenant_id: int | None = None
    role_level: int | None = None
    action: str
    target_type: str | None = None
    target_id: str | None = None
    method: str | None = None
    request_uri: str | None = None
    request_params: str | None = None
    result_status: str | None = None
    error_msg: str | None = None
    execution_ms: int | None = None
    client_ip: str | None = None
    created_at: datetime | None = None

    @field_serializer("created_at")
    def _serialize_dt(self, value: datetime | None) -> str | None:
        return _fmt(value)


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    file_path: str
    file_type: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    ref_count: int | None = None
    storage_type: str | None = None
    tenant_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    remark: str | None = None

    @field_serializer("created_at", "updated_at")
    def _serialize_dt(self, value: datetime | None) -> str | None:
        return _fmt(value)


class SubscriptionIn(BaseModel):
    target_type: str
    target_id: int
    channel: str | None = None
    enabled: int | None = None


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscriber_id: int
    target_type: str
    target_id: int
    channel: str | None = None
    enabled: int | None = None
    tenant_id: int | None = None
    created_at: datetime | None = None

    @field_serializer("created_at")
    def _serialize_dt(self, value: datetime | None) -> str | None:
        return _fmt(value)


class NotifyMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_id: int | None = None
    recipient_id: int
    title: str
    content: str | None = None
    channel: str | None = None
    status: str | None = None
    sent_time: datetime | None = None
    tenant_id: int | None = None
    created_at: datetime | None = None

    @field_serializer("sent_time", "created_at")
    def _serialize_dt(self, value: datetime | None) -> str | None:
        return _fmt(value)
