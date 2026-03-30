"""基础 Repository"""
from typing import Generic, TypeVar, Type, Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseRepository(Generic[ModelType]):
    """基础 Repository 类"""

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: int) -> Optional[ModelType]:
        """根据 ID 获取"""
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """获取所有"""
        result = await self.db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, obj: ModelType) -> ModelType:
        """创建"""
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelType) -> ModelType:
        """更新"""
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, id: int) -> bool:
        """删除"""
        obj = await self.get(id)
        if obj:
            await self.db.delete(obj)
            await self.db.flush()
            return True
        return False

    async def count(self) -> int:
        """计数"""
        result = await self.db.execute(select(self.model))
        return len(list(result.scalars().all()))
