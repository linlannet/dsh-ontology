"""系统层 ORM：用户/角色/审计/文件/通知，表名与 V1.0.0 DDL 一致。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dsh_onto_base import Base


class SysUser(Base):
    __tablename__ = "onto_sys_user"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger)
    role_level: Mapped[int] = mapped_column(Integer)
    user_name: Mapped[str] = mapped_column(String(50))
    nick_name: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(50))
    phonenumber: Mapped[str | None] = mapped_column(String(50))
    password: Mapped[str] = mapped_column(String(200))
    status: Mapped[str | None] = mapped_column(String(1))
    del_flag: Mapped[str | None] = mapped_column(String(1))
    login_ip: Mapped[str | None] = mapped_column(String(50))
    login_date: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_by: Mapped[str | None] = mapped_column(String(50))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    remark: Mapped[str | None] = mapped_column(String(800))


class SysRole(Base):
    __tablename__ = "onto_sys_role"

    role_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role_code: Mapped[str] = mapped_column(String(50))
    role_name: Mapped[str] = mapped_column(String(50))
    role_level: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str | None] = mapped_column(String(1))
    del_flag: Mapped[str | None] = mapped_column(String(1))
    created_by: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_by: Mapped[str | None] = mapped_column(String(50))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    remark: Mapped[str | None] = mapped_column(String(800))


class SysUserRole(Base):
    __tablename__ = "onto_sys_user_role"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    role_id: Mapped[int] = mapped_column(BigInteger)
    created_by: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime | None] = mapped_column(DateTime)


class SysAuditLog(Base):
    __tablename__ = "onto_sys_audit_log"

    log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger)
    role_level: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(50))
    target_type: Mapped[str | None] = mapped_column(String(100))
    target_id: Mapped[str | None] = mapped_column(String(100))
    method: Mapped[str | None] = mapped_column(String(200))
    request_uri: Mapped[str | None] = mapped_column(String(500))
    request_params: Mapped[str | None] = mapped_column(Text)
    result_status: Mapped[str | None] = mapped_column(String(20))
    error_msg: Mapped[str | None] = mapped_column(Text)
    execution_ms: Mapped[int | None] = mapped_column(BigInteger)
    client_ip: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime | None] = mapped_column(DateTime)


class CommonFile(Base):
    __tablename__ = "onto_common_file"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    file_name: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(1000))
    file_type: Mapped[str | None] = mapped_column(String(50))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    ref_count: Mapped[int | None] = mapped_column(Integer)
    storage_type: Mapped[str | None] = mapped_column(String(20))
    tenant_id: Mapped[int | None] = mapped_column(BigInteger)
    created_by: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_by: Mapped[str | None] = mapped_column(String(50))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    del_flag: Mapped[int | None] = mapped_column(Integer)
    remark: Mapped[str | None] = mapped_column(String(800))


class NotifySubscription(Base):
    __tablename__ = "onto_notify_subscription"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subscriber_id: Mapped[int] = mapped_column(BigInteger)
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[int] = mapped_column(BigInteger)
    channel: Mapped[str | None] = mapped_column(String(20))
    enabled: Mapped[int | None] = mapped_column(Integer)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger)
    created_by: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_by: Mapped[str | None] = mapped_column(String(50))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    del_flag: Mapped[int | None] = mapped_column(Integer)


class NotifyMessage(Base):
    __tablename__ = "onto_notify_message"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subscription_id: Mapped[int | None] = mapped_column(BigInteger)
    recipient_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str | None] = mapped_column(Text)
    channel: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str | None] = mapped_column(String(20))
    sent_time: Mapped[datetime | None] = mapped_column(DateTime)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger)
    created_by: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime | None] = mapped_column(DateTime)
