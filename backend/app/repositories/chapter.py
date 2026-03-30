"""Chapter Repository"""
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter, ChapterStatus
from app.repositories.base import BaseRepository


class ChapterRepository(BaseRepository[Chapter]):
    """章节仓储"""

    def __init__(self, db: AsyncSession):
        super().__init__(Chapter, db)

    async def get_by_project(self, project_id: int, skip: int = 0, limit: int = 100) -> list[Chapter]:
        """获取项目的所有章节"""
        result = await self.db.execute(
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .order_by(Chapter.chapter_no)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_volume(self, volume_id: int) -> list[Chapter]:
        """获取卷的所有章节"""
        result = await self.db.execute(
            select(Chapter)
            .where(Chapter.volume_id == volume_id)
            .order_by(Chapter.chapter_no)
        )
        return list(result.scalars().all())

    async def get_by_chapter_no(self, project_id: int, chapter_no: int) -> Optional[Chapter]:
        """根据章节号查找"""
        result = await self.db.execute(
            select(Chapter).where(
                and_(
                    Chapter.project_id == project_id,
                    Chapter.chapter_no == chapter_no
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_status(self, project_id: int, status: ChapterStatus) -> list[Chapter]:
        """根据状态查找章节"""
        result = await self.db.execute(
            select(Chapter)
            .where(
                and_(
                    Chapter.project_id == project_id,
                    Chapter.status == status
                )
            )
            .order_by(Chapter.chapter_no)
        )
        return list(result.scalars().all())

    async def get_next_chapter_no(self, project_id: int) -> int:
        """获取下一个章节号"""
        result = await self.db.execute(
            select(func.max(Chapter.chapter_no)).where(Chapter.project_id == project_id)
        )
        max_no = result.scalar_one_or_none()
        return (max_no or 0) + 1

    async def count_by_project(self, project_id: int) -> int:
        """统计项目章节数"""
        result = await self.db.execute(
            select(func.count(Chapter.id)).where(Chapter.project_id == project_id)
        )
        return result.scalar_one()

    async def get_recent_chapters(self, project_id: int, limit: int = 3) -> list[Chapter]:
        """获取最近的章节"""
        result = await self.db.execute(
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .order_by(Chapter.chapter_no.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
