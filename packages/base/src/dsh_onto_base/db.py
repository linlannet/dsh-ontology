"""双库会话：siis 项目库 + 平台本体库，引擎按需创建（P0 不连接数据库也可启动）。"""

from __future__ import annotations

from functools import cached_property

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有平台包 ORM 模型的统一基类，避免各包各自建元数据。"""


class Database:
    """双引擎容器。

    - ``siis_engine``：项目库（``dsh_java_siisdb``），项目层表 ``gwy_*``
    - ``onto_engine``：平台库（``dsh_java_ontodb``），平台表 ``onto_*``

    引擎在首次访问时才创建，避免无数据库环境下启动失败；驱动缺失时抛出明确错误。
    """

    def __init__(self, siis_url: str, onto_url: str, echo: bool = False) -> None:
        self._siis_url = siis_url
        self._onto_url = onto_url
        self._echo = echo

    def _build(self, url: str) -> AsyncEngine:
        return create_async_engine(url, echo=self._echo, pool_pre_ping=True, future=True)

    @cached_property
    def siis_engine(self) -> AsyncEngine:
        return self._build(self._siis_url)

    @cached_property
    def onto_engine(self) -> AsyncEngine:
        return self._build(self._onto_url)

    @cached_property
    def siis_session(self) -> async_sessionmaker:
        return async_sessionmaker(self.siis_engine, expire_on_commit=False)

    @cached_property
    def onto_session(self) -> async_sessionmaker:
        return async_sessionmaker(self.onto_engine, expire_on_commit=False)

    async def dispose(self) -> None:
        if "siis_engine" in self.__dict__:
            await self.siis_engine.dispose()
        if "onto_engine" in self.__dict__:
            await self.onto_engine.dispose()
