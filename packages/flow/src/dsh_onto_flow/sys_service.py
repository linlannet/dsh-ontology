"""系统层业务：认证、用户/角色、审计、文件、通知。"""

from __future__ import annotations

import json

import bcrypt
from fastapi import Request

from dsh_onto_base import Settings, create_token, tenant_id_var, user_id_var

from .sys_repository import SysRepository


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def _int_or_none(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


class SysService:
    def __init__(self, database, settings: Settings) -> None:
        self.repo = SysRepository(database)
        self.settings = settings

    # ---------------- 认证 ----------------
    async def login(self, user_name: str, password: str, client_ip: str | None) -> dict:
        user = await self.repo.find_user_by_name(user_name)
        if not user:
            raise ValueError("用户名或密码错误")
        if user.get("status") == "1":
            raise RuntimeError("账号已停用")
        if not verify_password(password, user.get("password")):
            raise ValueError("用户名或密码错误")
        await self.repo.update_login_info(user["user_id"], client_ip)
        return self._token_payload(user)

    async def register(
        self, user_name: str, password: str, nick_name: str | None, email: str | None,
        phonenumber: str | None, tenant_id: int | None,
    ) -> dict:
        if await self.repo.exists_user_name(user_name):
            raise ValueError("用户名已存在")
        user_id = await self.repo.insert_user(
            tenant_id=tenant_id if tenant_id is not None else 1,
            role_level=2,
            user_name=user_name,
            nick_name=nick_name,
            email=email,
            phonenumber=phonenumber,
            password=hash_password(password),
            status="0",
            created_by="register",
            remark=None,
        )
        user = {
            "user_id": user_id,
            "user_name": user_name,
            "nick_name": nick_name,
            "role_level": 2,
            "tenant_id": tenant_id if tenant_id is not None else 1,
        }
        return self._token_payload(user)

    def _token_payload(self, user: dict) -> dict:
        token = create_token(
            self.settings.jwt_secret,
            user["user_id"],
            user["user_name"],
            user["role_level"],
            user.get("tenant_id"),
            self.settings.jwt_expiration_ms,
        )
        return {
            "token": token,
            "user_id": user["user_id"],
            "user_name": user["user_name"],
            "nick_name": user.get("nick_name"),
            "role_level": user["role_level"],
            "tenant_id": user.get("tenant_id"),
        }

    async def current_user(self) -> dict | None:
        user_id = _int_or_none(user_id_var.get())
        if user_id is None:
            return None
        return await self.repo.find_user_by_id(user_id)

    async def change_password(self, user_id: int, old_password: str, new_password: str) -> int:
        user = await self.repo.find_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")
        if not verify_password(old_password, user.get("password")):
            raise ValueError("原密码错误")
        return await self.repo.update_password(user_id, hash_password(new_password), str(user_id))

    # ---------------- 用户管理 ----------------
    async def list_users(self) -> list[dict]:
        return await self.repo.find_all_users()

    async def page_users(self, page_num: int, page_size: int) -> list[dict]:
        return await self.repo.find_users_page(page_num, page_size)

    async def count_users(self) -> int:
        return await self.repo.count_users()

    async def find_user(self, user_id: int) -> dict | None:
        return await self.repo.find_user_by_id(user_id)

    async def update_user(self, user_id: int, values: dict, updated_by: str | None) -> int:
        return await self.repo.update_user(
            user_id,
            values.get("nick_name"),
            values.get("email"),
            values.get("phonenumber"),
            values.get("status"),
            values.get("remark"),
            updated_by,
        )

    async def delete_user(self, user_id: int) -> int:
        return await self.repo.soft_delete_user(user_id)

    # ---------------- 角色 ----------------
    async def list_roles(self) -> list[dict]:
        return await self.repo.find_all_roles()

    async def find_role(self, role_id: int) -> dict | None:
        return await self.repo.find_role_by_id(role_id)

    async def create_role(self, values: dict, created_by: str | None) -> int:
        return await self.repo.insert_role(
            role_code=values.get("role_code") or "",
            role_name=values.get("role_name") or "",
            role_level=values.get("role_level") if values.get("role_level") is not None else 2,
            description=values.get("description"),
            status=values.get("status"),
            created_by=created_by,
            remark=values.get("remark"),
        )

    async def update_role(self, role_id: int, values: dict, updated_by: str | None) -> int:
        return await self.repo.update_role(
            role_id,
            values.get("role_name"),
            values.get("role_level"),
            values.get("description"),
            values.get("status"),
            values.get("remark"),
            updated_by,
        )

    async def delete_role(self, role_id: int) -> int:
        return await self.repo.soft_delete_role(role_id)

    async def user_roles(self, user_id: int) -> list[dict]:
        return await self.repo.find_roles_by_user(user_id)

    async def assign_role(self, user_id: int, role_id: int, created_by: str | None) -> int:
        return await self.repo.assign_role(user_id, role_id, created_by)

    async def revoke_role(self, user_id: int, role_id: int) -> int:
        return await self.repo.revoke_role(user_id, role_id)

    # ---------------- 审计 ----------------
    async def audit_page(self, page_num: int, page_size: int, user_id: int | None = None,
                         action: str | None = None) -> list[dict]:
        return await self.repo.find_audit_page(page_num, page_size, user_id, action)

    async def audit_count(self) -> int:
        return await self.repo.count_audit()

    async def write_audit(self, request: Request, action: str, target_type: str,
                          target_id: str | None = None, status: str = "SUCCESS",
                          error_msg: str | None = None, execution_ms: int | None = None) -> None:
        """写入审计日志；失败不影响主流程（对齐 Java AOP 的非阻断语义）。"""
        try:
            await self.repo.insert_audit(
                user_id=_int_or_none(user_id_var.get()),
                tenant_id=_int_or_none(tenant_id_var.get()),
                role_level=None,
                action=action,
                target_type=target_type,
                target_id=target_id,
                method=request.method,
                request_uri=str(request.url.path),
                request_params=json.dumps(dict(request.query_params), ensure_ascii=False),
                result_status=status,
                error_msg=error_msg,
                execution_ms=execution_ms,
                client_ip=request.client.host if request.client else None,
            )
        except Exception:
            pass

    # ---------------- 文件 --------------
    async def find_file(self, file_id: int) -> dict | None:
        return await self.repo.find_file_by_id(file_id)

    async def page_files(self, tenant_id: int | None, page_num: int, page_size: int) -> list[dict]:
        return await self.repo.find_files_page(tenant_id if tenant_id is not None else 1,
                                               page_num, page_size)

    async def increment_file_ref(self, file_id: int) -> int:
        return await self.repo.increment_file_ref(file_id)

    async def decrement_file_ref(self, file_id: int) -> int:
        return await self.repo.decrement_file_ref(file_id)

    async def delete_file(self, file_id: int) -> int:
        return await self.repo.soft_delete_file(file_id)

    # ---------------- 通知 --------------
    async def subscribe(self, subscriber_id: int | None, target_type: str, target_id: int,
                        channel: str | None, enabled: int | None) -> int:
        return await self.repo.insert_subscription(
            subscriber_id=subscriber_id or 0,
            target_type=target_type,
            target_id=target_id,
            channel=channel,
            enabled=enabled,
            tenant_id=_int_or_none(tenant_id_var.get()),
            created_by=str(user_id_var.get() or ""),
        )

    async def unsubscribe(self, sub_id: int) -> int:
        return await self.repo.delete_subscription(sub_id)

    async def my_subscriptions(self, subscriber_id: int | None) -> list[dict]:
        return await self.repo.find_subscriptions_by_subscriber(subscriber_id or 0)

    async def my_messages(self, recipient_id: int | None, page_num: int, page_size: int) -> list[dict]:
        return await self.repo.find_messages_by_recipient(recipient_id or 0, page_num, page_size)

    async def notify_subscribers(self, target_type: str, target_id: int, title: str,
                                 content: str) -> int:
        subs = await self.repo.find_subscriptions_by_target(target_type, target_id)
        count = 0
        for sub in subs:
            msg_id = await self.repo.insert_message(
                subscription_id=sub.get("id"),
                recipient_id=sub["subscriber_id"],
                title=title,
                content=content,
                channel=sub.get("channel"),
                status="PENDING",
                tenant_id=sub.get("tenant_id"),
                created_by="system",
            )
            await self.repo.mark_message_sent(msg_id)
            count += 1
        return count
