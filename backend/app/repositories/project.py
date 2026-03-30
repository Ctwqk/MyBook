"""Project Repository"""
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectStatus
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """项目仓储"""

    def __init__(self, db: AsyncSession):
        super().__init__(Project, db)

    async def get_by_title(self, title: str) -> Optional[Project]:
        """根据标题查找"""
        result = await self.db.execute(
            select(Project).where(Project.title == title)
        )
        return result.scalar_one_or_none()

    async def get_by_status(self, status: ProjectStatus, skip: int = 0, limit: int = 100) -> list[Project]:
        """根据状态查找"""
        result = await self.db.execute(
            select(Project)
            .where(Project.status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_status(self, status: ProjectStatus) -> int:
        """按状态计数"""
        result = await self.db.execute(
            select(func.count(Project.id)).where(Project.status == status)
        )
        return result.scalar_one()
