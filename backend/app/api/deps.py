"""API 依赖注入"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider
from app.services.planner.service import PlannerService
from app.services.memory.service import MemoryService
from app.services.writer.service import WriterService
from app.services.reviewer.service import ReviewerService
from app.services.publish.service import PublishService


# Database session
AsyncDBSession = Annotated[AsyncSession, Depends(get_db)]

# LLM Provider
LLMProviderType = Annotated[LLMProvider, Depends(get_llm_provider)]


def get_planner_service(
    db: AsyncDBSession,
    llm: LLMProviderType
) -> PlannerService:
    """获取 Planner Service"""
    return PlannerService(db, llm)


def get_memory_service(db: AsyncDBSession) -> MemoryService:
    """获取 Memory Service"""
    return MemoryService(db)


def get_writer_service(
    db: AsyncDBSession,
    llm: LLMProviderType
) -> WriterService:
    """获取 Writer Service"""
    return WriterService(db, llm)


def get_reviewer_service(
    db: AsyncDBSession,
    llm: LLMProviderType
) -> ReviewerService:
    """获取 Reviewer Service"""
    return ReviewerService(db, llm)


def get_publish_service(db: AsyncDBSession) -> PublishService:
    """获取 Publish Service"""
    return PublishService(db)


# Type aliases for cleaner route signatures
PlannerServiceType = Annotated[PlannerService, Depends(get_planner_service)]
MemoryServiceType = Annotated[MemoryService, Depends(get_memory_service)]
WriterServiceType = Annotated[WriterService, Depends(get_writer_service)]
ReviewerServiceType = Annotated[ReviewerService, Depends(get_reviewer_service)]
PublishServiceType = Annotated[PublishService, Depends(get_publish_service)]
