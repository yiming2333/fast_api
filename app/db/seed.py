"""数据库种子脚本。

首次启动时创建默认管理员账户（如果不存在）。
生产环境应通过 /api/v1/users/ 注册或单独的管理脚本创建用户。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security import get_password_hash
from app.models.user import UserORM
from app.db.session import get_session_maker


async def seed_default_user() -> None:
    """创建默认管理员用户 alice（如果不存在）。"""
    session_maker = get_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(UserORM).where(UserORM.username == "alice")
        )
        if result.scalar_one_or_none() is not None:
            return  # 已存在，跳过

        user = UserORM(
            username="alice",
            email="alice@example.com",
            full_name="Alice Wonderson",
            hashed_password=get_password_hash("secret"),
            disabled=False,
        )
        session.add(user)
        await session.commit()
        logger.info("已创建默认用户 alice（密码: secret）")
