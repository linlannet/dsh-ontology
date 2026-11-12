"""系统层路由：认证/用户/角色/审计/文件/通知/SSE 排障。

与 Java 版对齐点：
- 登录/注册为公开端点，其余按 ``@RequiresRole`` 层级校验；
- 业务错误以 HTTP 200 + ``Result`` 业务码返回（对齐 Spring 控制器内 try/catch）；
- 写操作落审计日志（非阻断）。
"""

from __future__ import annotations

import asyncio
import os
import threading
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from dsh_onto_base import fail, ok, require_role, tenant_id_var, user_id_var

from .sys_schemas import (
    LoginIn,
    NotifyMessageOut,
    RegisterIn,
    RoleIn,
    SubscriptionIn,
    UserUpdateIn,
)
from .sys_service import SysService, _int_or_none

public_auth_router = APIRouter(prefix="/api/auth", tags=["sys"])
auth_router = APIRouter(prefix="/api/auth", tags=["sys"], dependencies=[Depends(require_role(2))])
user_router = APIRouter(prefix="/api/auth/user", tags=["sys"], dependencies=[Depends(require_role(0))])
role_router = APIRouter(prefix="/api/auth/role", tags=["sys"], dependencies=[Depends(require_role(0))])
audit_router = APIRouter(prefix="/api/auth/audit-log", tags=["sys"], dependencies=[Depends(require_role(0))])
notify_router = APIRouter(prefix="/api/notify", tags=["sys"], dependencies=[Depends(require_role(2))])
file_router = APIRouter(prefix="/api/file", tags=["sys"], dependencies=[Depends(require_role(2))])
debug_router = APIRouter(prefix="/api/debug", tags=["sys"], dependencies=[Depends(require_role(0))])


def _service(request: Request) -> SysService:
    return SysService(request.app.state.database, request.app.state.settings)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


# ---------------- 认证 ----------------
@public_auth_router.post("/login")
async def login(payload: LoginIn, request: Request):
    try:
        data = await _service(request).login(payload.user_name, payload.password, _client_ip(request))
        return ok(data)
    except ValueError as exc:
        return fail(str(exc), code=400)
    except RuntimeError as exc:
        return fail(str(exc))


@public_auth_router.post("/register")
async def register(payload: RegisterIn, request: Request):
    try:
        data = await _service(request).register(
            payload.user_name, payload.password, payload.nick_name,
            payload.email, payload.phonenumber, payload.tenant_id,
        )
        return ok(data)
    except ValueError as exc:
        return fail(str(exc), code=400)


@auth_router.get("/userinfo")
async def userinfo(request: Request):
    user = await _service(request).current_user()
    if user is None:
        return fail("未登录" if user_id_var.get() is None else "用户不存在", code=401)
    from .sys_schemas import UserInfoOut

    return ok(UserInfoOut.model_validate(user).model_dump())


@auth_router.put("/password")
async def change_password(request: Request, oldPassword: str, newPassword: str):
    user_id = _int_or_none(user_id_var.get())
    if user_id is None:
        return fail("未登录", code=401)
    try:
        rows = await _service(request).change_password(user_id, oldPassword, newPassword)
        return ok(rows)
    except ValueError as exc:
        return fail(str(exc), code=400)


# ---------------- 用户管理 ----------------
@user_router.get("")
async def list_users(request: Request):
    from .sys_schemas import UserInfoOut

    users = await _service(request).list_users()
    return ok([UserInfoOut.model_validate(u).model_dump() for u in users])


@user_router.get("/page")
async def page_users(request: Request, pageNum: int = 1, pageSize: int = 10):
    from .sys_schemas import UserInfoOut

    users = await _service(request).page_users(pageNum, pageSize)
    return ok([UserInfoOut.model_validate(u).model_dump() for u in users])


@user_router.get("/count")
async def count_users(request: Request):
    return ok(await _service(request).count_users())


@user_router.get("/{user_id}")
async def get_user(user_id: int, request: Request):
    user = await _service(request).find_user(user_id)
    return ok(user) if user else fail(f"用户不存在: {user_id}", code=404)


@user_router.put("/{user_id}")
async def update_user(user_id: int, payload: UserUpdateIn, request: Request):
    started = time.time()
    rows = await _service(request).update_user(
        user_id, payload.model_dump(), str(user_id_var.get())
    )
    await _service(request).write_audit(
        request, "UPDATE", "sys_user", str(user_id), execution_ms=int((time.time() - started) * 1000)
    )
    return ok(rows)


@user_router.delete("/{user_id}")
async def delete_user(user_id: int, request: Request):
    started = time.time()
    rows = await _service(request).delete_user(user_id)
    await _service(request).write_audit(
        request, "DELETE", "sys_user", str(user_id), execution_ms=int((time.time() - started) * 1000)
    )
    return ok(rows)


# ---------------- 角色 ----------------
@role_router.get("")
async def list_roles(request: Request):
    from .sys_schemas import RoleOut

    roles = await _service(request).list_roles()
    return ok([RoleOut.model_validate(r).model_dump() for r in roles])


@role_router.get("/{role_id}")
async def get_role(role_id: int, request: Request):
    from .sys_schemas import RoleOut

    role = await _service(request).find_role(role_id)
    return ok(RoleOut.model_validate(role).model_dump()) if role else fail(
        f"角色不存在: {role_id}", code=404
    )


@role_router.post("")
async def create_role(payload: RoleIn, request: Request):
    started = time.time()
    role_id = await _service(request).create_role(
        payload.model_dump(), str(user_id_var.get())
    )
    await _service(request).write_audit(
        request, "CREATE", "sys_role", str(role_id), execution_ms=int((time.time() - started) * 1000)
    )
    return ok(role_id)


@role_router.put("/{role_id}")
async def update_role(role_id: int, payload: RoleIn, request: Request):
    started = time.time()
    rows = await _service(request).update_role(
        role_id, payload.model_dump(), str(user_id_var.get())
    )
    await _service(request).write_audit(
        request, "UPDATE", "sys_role", str(role_id), execution_ms=int((time.time() - started) * 1000)
    )
    return ok(rows)


@role_router.delete("/{role_id}")
async def delete_role(role_id: int, request: Request):
    started = time.time()
    rows = await _service(request).delete_role(role_id)
    await _service(request).write_audit(
        request, "DELETE", "sys_role", str(role_id), execution_ms=int((time.time() - started) * 1000)
    )
    return ok(rows)


@role_router.get("/user/{user_id}")
async def user_roles(user_id: int, request: Request):
    from .sys_schemas import RoleOut

    roles = await _service(request).user_roles(user_id)
    return ok([RoleOut.model_validate(r).model_dump() for r in roles])


@role_router.post("/user/{user_id}/assign/{role_id}")
async def assign_role(user_id: int, role_id: int, request: Request):
    started = time.time()
    rows = await _service(request).assign_role(user_id, role_id, str(user_id_var.get()))
    await _service(request).write_audit(
        request, "ASSIGN_ROLE", "sys_user_role", f"{user_id}:{role_id}",
        execution_ms=int((time.time() - started) * 1000),
    )
    return ok(rows)


@role_router.delete("/user/{user_id}/revoke/{role_id}")
async def revoke_role(user_id: int, role_id: int, request: Request):
    started = time.time()
    rows = await _service(request).revoke_role(user_id, role_id)
    await _service(request).write_audit(
        request, "REVOKE_ROLE", "sys_user_role", f"{user_id}:{role_id}",
        execution_ms=int((time.time() - started) * 1000),
    )
    return ok(rows)


# ---------------- 审计 ----------------
@audit_router.get("/page")
async def audit_page(request: Request, pageNum: int = 1, pageSize: int = 20):
    from .sys_schemas import AuditLogOut

    rows = await _service(request).audit_page(pageNum, pageSize)
    return ok([AuditLogOut.model_validate(r).model_dump() for r in rows])


@audit_router.get("/user/{user_id}")
async def audit_by_user(user_id: int, request: Request, pageNum: int = 1, pageSize: int = 20):
    from .sys_schemas import AuditLogOut

    rows = await _service(request).audit_page(pageNum, pageSize, user_id=user_id)
    return ok([AuditLogOut.model_validate(r).model_dump() for r in rows])


@audit_router.get("/action/{action}")
async def audit_by_action(action: str, request: Request, pageNum: int = 1, pageSize: int = 20):
    from .sys_schemas import AuditLogOut

    rows = await _service(request).audit_page(pageNum, pageSize, action=action)
    return ok([AuditLogOut.model_validate(r).model_dump() for r in rows])


@audit_router.get("/count")
async def audit_count(request: Request):
    return ok(await _service(request).audit_count())


# ---------------- 文件 ----------------
@file_router.get("/page")
async def page_files(request: Request, pageNum: int = 1, pageSize: int = 20):
    from .sys_schemas import FileOut

    rows = await _service(request).page_files(_int_or_none(tenant_id_var.get()), pageNum, pageSize)
    return ok([FileOut.model_validate(r).model_dump() for r in rows])


@file_router.get("/{file_id}")
async def get_file(file_id: int, request: Request):
    from .sys_schemas import FileOut

    row = await _service(request).find_file(file_id)
    return ok(FileOut.model_validate(row).model_dump()) if row else fail(
        f"文件不存在: {file_id}", code=404
    )


@file_router.post("/{file_id}/ref/increment")
async def increment_file_ref(file_id: int, request: Request):
    started = time.time()
    rows = await _service(request).increment_file_ref(file_id)
    await _service(request).write_audit(
        request, "REF_INCREMENT", "common_file", str(file_id),
        execution_ms=int((time.time() - started) * 1000),
    )
    return ok(rows)


@file_router.post("/{file_id}/ref/decrement")
async def decrement_file_ref(file_id: int, request: Request):
    started = time.time()
    rows = await _service(request).decrement_file_ref(file_id)
    await _service(request).write_audit(
        request, "REF_DECREMENT", "common_file", str(file_id),
        execution_ms=int((time.time() - started) * 1000),
    )
    return ok(rows)


@file_router.delete("/{file_id}")
async def delete_file(file_id: int, request: Request):
    started = time.time()
    rows = await _service(request).delete_file(file_id)
    await _service(request).write_audit(
        request, "DELETE", "common_file", str(file_id),
        execution_ms=int((time.time() - started) * 1000),
    )
    return ok(rows)


# ---------------- 通知 ----------------
@notify_router.post("/subscribe", dependencies=[Depends(require_role(1))])
async def subscribe(payload: SubscriptionIn, request: Request):
    started = time.time()
    sub_id = await _service(request).subscribe(
        _int_or_none(user_id_var.get()), payload.target_type, payload.target_id,
        payload.channel, payload.enabled,
    )
    await _service(request).write_audit(
        request, "SUBSCRIBE", "notify_subscription", str(sub_id),
        execution_ms=int((time.time() - started) * 1000),
    )
    return ok(sub_id)


@notify_router.delete("/subscribe/{sub_id}", dependencies=[Depends(require_role(1))])
async def unsubscribe(sub_id: int, request: Request):
    started = time.time()
    rows = await _service(request).unsubscribe(sub_id)
    await _service(request).write_audit(
        request, "UNSUBSCRIBE", "notify_subscription", str(sub_id),
        execution_ms=int((time.time() - started) * 1000),
    )
    return ok(rows)


@notify_router.get("/my-subscriptions")
async def my_subscriptions(request: Request):
    from .sys_schemas import SubscriptionOut

    rows = await _service(request).my_subscriptions(_int_or_none(user_id_var.get()))
    return ok([SubscriptionOut.model_validate(r).model_dump() for r in rows])


@notify_router.get("/my-messages")
async def my_messages(request: Request, pageNum: int = 1, pageSize: int = 20):
    rows = await _service(request).my_messages(_int_or_none(user_id_var.get()), pageNum, pageSize)
    return ok([NotifyMessageOut.model_validate(r).model_dump() for r in rows])


@notify_router.post("/send", dependencies=[Depends(require_role(0))])
async def send_notify(request: Request, targetType: str, targetId: int, title: str, content: str):
    started = time.time()
    count = await _service(request).notify_subscribers(targetType, targetId, title, content)
    await _service(request).write_audit(
        request, "NOTIFY_SEND", "notify_message", f"{targetType}:{targetId}",
        execution_ms=int((time.time() - started) * 1000),
    )
    return ok(count)


# ---------------- SSE 排障 ----------------
def _rss_mb() -> int:
    try:
        with open("/proc/self/statm", "rb") as fh:
            pages = int(fh.read().split()[1])
        return pages * os.sysconf("SC_PAGE_SIZE") // (1024 * 1024)
    except Exception:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # macOS 以字节返回，Linux 以 KB 返回
        return usage // (1024 * 1024) if usage > 1_000_000 else usage // 1024


@debug_router.get("/stream")
async def debug_stream(request: Request):
    """对齐 Java SseDebugController：每 2 秒推送一次 stats，最长 60 秒。"""

    async def event_generator():
        deadline = time.time() + 60
        while time.time() < deadline:
            payload = (
                f'{{"heapMB":{_rss_mb()},"threads":{threading.active_count()},'
                f'"time":{int(time.time() * 1000)}}}'
            )
            yield f"event: stats\ndata: {payload}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


ALL_SYS_ROUTERS = (
    public_auth_router,
    auth_router,
    user_router,
    role_router,
    audit_router,
    notify_router,
    file_router,
    debug_router,
)
