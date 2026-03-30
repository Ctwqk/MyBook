#!/usr/bin/env python
"""数据库迁移脚本"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.db.session import Base
from app.models import *  # 导入所有模型


async def init_db():
    """初始化数据库"""
    settings = get_settings()
    
    engine = create_async_engine(settings.database_url, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("数据库初始化完成!")


if __name__ == "__main__":
    asyncio.run(init_db())
