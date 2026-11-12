"""系统层数据访问：SQL 与 Java ``sys/repository`` 保持一致，统一走平台库会话。"""

from __future__ import annotations

from sqlalchemy import text

from dsh_onto_base import Database


class SysRepository:
    def __init__(self, database: Database) -> None:
        self._db = database

    async def _fetch_all(self, sql: str, **params) -> list[dict]:
        async with self._db.onto_session() as session:
            rows = await session.execute(text(sql), params)
            return [dict(r) for r in rows.mappings()]

    async def _fetch_one(self, sql: str, **params) -> dict | None:
        rows = await self._fetch_all(sql, **params)
        return rows[0] if rows else None

    async def _scalar(self, sql: str, **params) -> int:
        async with self._db.onto_session() as session:
            value = (await session.execute(text(sql), params)).scalar()
            return int(value or 0)

    async def _insert(self, sql: str, **params) -> int:
        async with self._db.onto_session() as session:
            result = await session.execute(text(sql), params)
            await session.commit()
            return int(result.lastrowid or 0)

    async def _write(self, sql: str, **params) -> int:
        async with self._db.onto_session() as session:
            result = await session.execute(text(sql), params)
            await session.commit()
            return int(result.rowcount or 0)

    # ---------------- 用户 ----------------
    async def find_user_by_name(self, user_name: str) -> dict | None:
        return await self._fetch_one(
            "SELECT * FROM onto_sys_user WHERE user_name = :user_name AND del_flag = '0'",
            user_name=user_name,
        )

    async def find_user_by_id(self, user_id: int) -> dict | None:
        return await self._fetch_one(
            "SELECT * FROM onto_sys_user WHERE user_id = :user_id AND del_flag = '0'", user_id=user_id
        )

    async def find_all_users(self) -> list[dict]:
        return await self._fetch_all(
            "SELECT * FROM onto_sys_user WHERE del_flag = '0' ORDER BY user_id"
        )

    async def find_users_page(self, page_num: int, page_size: int) -> list[dict]:
        return await self._fetch_all(
            "SELECT * FROM onto_sys_user WHERE del_flag = '0' ORDER BY user_id "
            "LIMIT :limit OFFSET :offset",
            limit=page_size,
            offset=(page_num - 1) * page_size,
        )

    async def count_users(self) -> int:
        return await self._scalar("SELECT COUNT(*) FROM onto_sys_user WHERE del_flag = '0'")

    async def insert_user(
        self, tenant_id: int | None, role_level: int, user_name: str, nick_name: str | None,
        email: str | None, phonenumber: str | None, password: str, status: str | None,
        created_by: str | None, remark: str | None,
    ) -> int:
        return await self._insert(
            "INSERT INTO onto_sys_user (tenant_id, role_level, user_name, nick_name, email, "
            "phonenumber, password, status, del_flag, created_by, remark) "
            "VALUES (:tenant_id, :role_level, :user_name, :nick_name, :email, :phonenumber, "
            ":password, :status, '0', :created_by, :remark)",
            tenant_id=tenant_id, role_level=role_level, user_name=user_name, nick_name=nick_name,
            email=email, phonenumber=phonenumber, password=password, status=status or "0",
            created_by=created_by, remark=remark,
        )

    async def update_user(
        self, user_id: int, nick_name: str | None, email: str | None,
        phonenumber: str | None, status: str | None, remark: str | None, updated_by: str | None,
    ) -> int:
        return await self._write(
            "UPDATE onto_sys_user SET nick_name = :nick_name, email = :email, "
            "phonenumber = :phonenumber, status = :status, updated_by = :updated_by, "
            "updated_at = NOW(), remark = :remark WHERE user_id = :user_id AND del_flag = '0'",
            user_id=user_id, nick_name=nick_name, email=email, phonenumber=phonenumber,
            status=status, remark=remark, updated_by=updated_by,
        )

    async def update_password(self, user_id: int, password: str, updated_by: str | None) -> int:
        return await self._write(
            "UPDATE onto_sys_user SET password = :password, updated_by = :updated_by, "
            "updated_at = NOW() WHERE user_id = :user_id AND del_flag = '0'",
            user_id=user_id, password=password, updated_by=updated_by,
        )

    async def update_login_info(self, user_id: int, login_ip: str | None) -> int:
        return await self._write(
            "UPDATE onto_sys_user SET login_ip = :login_ip, login_date = NOW() WHERE user_id = :user_id",
            user_id=user_id, login_ip=login_ip,
        )

    async def soft_delete_user(self, user_id: int) -> int:
        return await self._write(
            "UPDATE onto_sys_user SET del_flag = '1', updated_at = NOW() "
            "WHERE user_id = :user_id AND del_flag = '0'", user_id=user_id,
        )

    async def exists_user_name(self, user_name: str) -> bool:
        return await self._scalar(
            "SELECT COUNT(*) FROM onto_sys_user WHERE user_name = :user_name AND del_flag = '0'",
            user_name=user_name,
        ) > 0

    # ---------------- 角色 ----------------
    async def find_all_roles(self) -> list[dict]:
        return await self._fetch_all(
            "SELECT * FROM onto_sys_role WHERE del_flag = '0' ORDER BY role_level"
        )

    async def find_role_by_id(self, role_id: int) -> dict | None:
        return await self._fetch_one(
            "SELECT * FROM onto_sys_role WHERE role_id = :role_id AND del_flag = '0'", role_id=role_id
        )

    async def find_role_by_code(self, role_code: str) -> dict | None:
        return await self._fetch_one(
            "SELECT * FROM onto_sys_role WHERE role_code = :role_code AND del_flag = '0'",
            role_code=role_code,
        )

    async def insert_role(
        self, role_code: str, role_name: str, role_level: int, description: str | None,
        status: str | None, created_by: str | None, remark: str | None,
    ) -> int:
        return await self._insert(
            "INSERT INTO onto_sys_role (role_code, role_name, role_level, description, status, "
            "del_flag, created_by, remark) VALUES (:role_code, :role_name, :role_level, "
            ":description, :status, '0', :created_by, :remark)",
            role_code=role_code, role_name=role_name, role_level=role_level,
            description=description, status=status or "0", created_by=created_by, remark=remark,
        )

    async def update_role(
        self, role_id: int, role_name: str | None, role_level: int | None,
        description: str | None, status: str | None, remark: str | None,
        updated_by: str | None,
    ) -> int:
        return await self._write(
            "UPDATE onto_sys_role SET role_name = :role_name, role_level = :role_level, "
            "description = :description, status = :status, updated_by = :updated_by, "
            "updated_at = NOW(), remark = :remark WHERE role_id = :role_id AND del_flag = '0'",
            role_id=role_id, role_name=role_name, role_level=role_level, description=description,
            status=status, remark=remark, updated_by=updated_by,
        )

    async def soft_delete_role(self, role_id: int) -> int:
        return await self._write(
            "UPDATE onto_sys_role SET del_flag = '1', updated_at = NOW() WHERE role_id = :role_id",
            role_id=role_id,
        )

    async def find_roles_by_user(self, user_id: int) -> list[dict]:
        return await self._fetch_all(
            "SELECT r.* FROM onto_sys_role r INNER JOIN onto_sys_user_role ur "
            "ON r.role_id = ur.role_id WHERE ur.user_id = :user_id AND r.del_flag = '0' "
            "ORDER BY r.role_level",
            user_id=user_id,
        )

    async def assign_role(self, user_id: int, role_id: int, created_by: str | None) -> int:
        return await self._write(
            "INSERT INTO onto_sys_user_role (user_id, role_id, created_by) "
            "VALUES (:user_id, :role_id, :created_by) ON DUPLICATE KEY UPDATE created_by = :created_by",
            user_id=user_id, role_id=role_id, created_by=created_by,
        )

    async def revoke_role(self, user_id: int, role_id: int) -> int:
        return await self._write(
            "DELETE FROM onto_sys_user_role WHERE user_id = :user_id AND role_id = :role_id",
            user_id=user_id, role_id=role_id,
        )

    # ---------------- 审计 ----------------
    async def insert_audit(
        self, user_id: int | None, tenant_id: int | None, role_level: int | None,
        action: str, target_type: str | None, target_id: str | None, method: str | None,
        request_uri: str | None, request_params: str | None, result_status: str | None,
        error_msg: str | None, execution_ms: int | None, client_ip: str | None,
    ) -> int:
        return await self._insert(
            "INSERT INTO onto_sys_audit_log (user_id, tenant_id, role_level, action, target_type, "
            "target_id, method, request_uri, request_params, result_status, error_msg, "
            "execution_ms, client_ip) VALUES (:user_id, :tenant_id, :role_level, :action, "
            ":target_type, :target_id, :method, :request_uri, :request_params, :result_status, "
            ":error_msg, :execution_ms, :client_ip)",
            user_id=user_id, tenant_id=tenant_id, role_level=role_level, action=action,
            target_type=target_type, target_id=target_id, method=method, request_uri=request_uri,
            request_params=request_params, result_status=result_status, error_msg=error_msg,
            execution_ms=execution_ms, client_ip=client_ip,
        )

    async def find_audit_page(self, page_num: int, page_size: int, user_id: int | None = None,
                              action: str | None = None) -> list[dict]:
        where, params = "", {"limit": page_size, "offset": (page_num - 1) * page_size}
        if user_id is not None:
            where += " WHERE user_id = :user_id"
            params["user_id"] = user_id
        if action is not None:
            where += (" AND" if where else " WHERE") + " action = :action"
            params["action"] = action
        return await self._fetch_all(
            f"SELECT * FROM onto_sys_audit_log{where} ORDER BY log_id DESC "
            "LIMIT :limit OFFSET :offset", **params,
        )

    async def count_audit(self) -> int:
        return await self._scalar("SELECT COUNT(*) FROM onto_sys_audit_log")

    # ---------------- 文件 ----------------
    async def insert_file(
        self, file_name: str, file_path: str, file_type: str | None, file_size: int | None,
        mime_type: str | None, storage_type: str | None, tenant_id: int | None,
        created_by: str | None, remark: str | None,
    ) -> int:
        return await self._insert(
            "INSERT INTO onto_common_file (file_name, file_path, file_type, file_size, mime_type, "
            "ref_count, storage_type, tenant_id, created_by, remark) VALUES (:file_name, "
            ":file_path, :file_type, :file_size, :mime_type, 0, :storage_type, :tenant_id, "
            ":created_by, :remark)",
            file_name=file_name, file_path=file_path, file_type=file_type, file_size=file_size,
            mime_type=mime_type, storage_type=storage_type or "LOCAL", tenant_id=tenant_id,
            created_by=created_by, remark=remark,
        )

    async def find_file_by_id(self, file_id: int) -> dict | None:
        return await self._fetch_one(
            "SELECT * FROM onto_common_file WHERE id = :id AND del_flag = 0", id=file_id
        )

    async def find_files_page(self, tenant_id: int, page_num: int, page_size: int) -> list[dict]:
        return await self._fetch_all(
            "SELECT * FROM onto_common_file WHERE tenant_id = :tenant_id AND del_flag = 0 "
            "ORDER BY id DESC LIMIT :limit OFFSET :offset",
            tenant_id=tenant_id, limit=page_size, offset=(page_num - 1) * page_size,
        )

    async def increment_file_ref(self, file_id: int) -> int:
        return await self._write(
            "UPDATE onto_common_file SET ref_count = ref_count + 1 WHERE id = :id AND del_flag = 0",
            id=file_id,
        )

    async def decrement_file_ref(self, file_id: int) -> int:
        return await self._write(
            "UPDATE onto_common_file SET ref_count = ref_count - 1 "
            "WHERE id = :id AND del_flag = 0 AND ref_count > 0", id=file_id,
        )

    async def soft_delete_file(self, file_id: int) -> int:
        return await self._write(
            "UPDATE onto_common_file SET del_flag = 1, updated_at = NOW() WHERE id = :id",
            id=file_id,
        )

    # ---------------- 通知 ----------------
    async def insert_subscription(
        self, subscriber_id: int, target_type: str, target_id: int, channel: str | None,
        enabled: int | None, tenant_id: int | None, created_by: str | None,
    ) -> int:
        return await self._insert(
            "INSERT INTO onto_notify_subscription (subscriber_id, target_type, target_id, channel, "
            "enabled, tenant_id, created_by) VALUES (:subscriber_id, :target_type, :target_id, "
            ":channel, :enabled, :tenant_id, :created_by)",
            subscriber_id=subscriber_id, target_type=target_type, target_id=target_id,
            channel=channel or "email", enabled=1 if enabled is None else enabled,
            tenant_id=tenant_id, created_by=created_by,
        )

    async def find_subscriptions_by_target(self, target_type: str, target_id: int) -> list[dict]:
        return await self._fetch_all(
            "SELECT * FROM onto_notify_subscription WHERE target_type = :target_type "
            "AND target_id = :target_id AND enabled = 1 AND del_flag = 0",
            target_type=target_type, target_id=target_id,
        )

    async def find_subscriptions_by_subscriber(self, subscriber_id: int) -> list[dict]:
        return await self._fetch_all(
            "SELECT * FROM onto_notify_subscription WHERE subscriber_id = :subscriber_id "
            "AND del_flag = 0 ORDER BY id DESC", subscriber_id=subscriber_id,
        )

    async def delete_subscription(self, sub_id: int) -> int:
        return await self._write(
            "UPDATE onto_notify_subscription SET del_flag = 1, updated_at = NOW() WHERE id = :id",
            id=sub_id,
        )

    async def insert_message(
        self, subscription_id: int | None, recipient_id: int, title: str, content: str | None,
        channel: str | None, status: str | None, tenant_id: int | None, created_by: str | None,
    ) -> int:
        return await self._insert(
            "INSERT INTO onto_notify_message (subscription_id, recipient_id, title, content, "
            "channel, status, tenant_id, created_by) VALUES (:subscription_id, :recipient_id, "
            ":title, :content, :channel, :status, :tenant_id, :created_by)",
            subscription_id=subscription_id, recipient_id=recipient_id, title=title,
            content=content, channel=channel or "email", status=status or "PENDING",
            tenant_id=tenant_id, created_by=created_by,
        )

    async def mark_message_sent(self, message_id: int) -> int:
        return await self._write(
            "UPDATE onto_notify_message SET status = 'SENT', sent_time = NOW() WHERE id = :id",
            id=message_id,
        )

    async def find_messages_by_recipient(self, recipient_id: int, page_num: int,
                                         page_size: int) -> list[dict]:
        return await self._fetch_all(
            "SELECT * FROM onto_notify_message WHERE recipient_id = :recipient_id "
            "ORDER BY id DESC LIMIT :limit OFFSET :offset",
            recipient_id=recipient_id, limit=page_size, offset=(page_num - 1) * page_size,
        )
