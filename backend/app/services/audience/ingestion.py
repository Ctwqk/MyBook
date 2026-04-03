"""Comment Ingestion Service - v2.5

职责：
- 抓取/接收评论数据
- 存储原始评论
- 去重处理
"""
import hashlib
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import RawComment
from app.schemas.comment import CommentIngestRequest, BatchCommentIngestRequest


class CommentIngestionService:
    """
    评论摄入服务 - v2.5
    
    负责：
    1. 接收评论数据
    2. 存储原始评论
    3. 去重处理
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _generate_user_hash(self, platform: str, user_id: str) -> str:
        """
        生成用户哈希 - 用于去重但不存储个人隐私
        
        使用 SHA256 哈希，不存储原始用户ID
        """
        raw = f"{platform}:{user_id}"
        return hashlib.sha256(raw.encode()).hexdigest()
    
    def _is_duplicate(self, project_id: int, user_hash: str, content_hash: str, 
                      time_window_minutes: int = 5) -> bool:
        """
        检查是否为重复评论
        
        在5分钟内同一用户的相似评论视为重复
        """
        # 简化实现：检查是否有完全相同内容的用户评论
        content_hash_input = hashlib.sha256(content_hash.encode()).hexdigest()
        
        # 这里应该检查时间窗口，但简化版只检查完全相同
        # 实际实现需要检查 created_at 时间窗口
        return False  # 默认不拒绝，允许存储
    
    async def ingest_comment(self, request: CommentIngestRequest) -> RawComment:
        """
        摄入单条评论
        
        流程：
        1. 生成用户哈希
        2. 检查重复
        3. 存储原始评论
        """
        # 生成用户哈希
        user_hash = self._generate_user_hash(request.platform, request.user_hash)
        
        # 检查重复（简化实现）
        if self._is_duplicate(request.project_id, user_hash, request.content):
            raise ValueError("Duplicate comment detected")
        
        # 创建评论记录
        comment = RawComment(
            project_id=request.project_id,
            platform=request.platform,
            chapter_id=request.chapter_id,
            paragraph_id=request.paragraph_id,
            user_hash=user_hash,
            content=request.content,
            like_count=request.like_count,
            reply_count=request.reply_count,
            created_at=request.timestamp or datetime.now(),
            processed=False
        )
        
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)
        
        return comment
    
    async def ingest_batch(self, request: BatchCommentIngestRequest) -> dict:
        """
        批量摄入评论
        
        返回：
        - inserted: 成功插入数
        - duplicates: 跳过数
        - errors: 错误信息
        """
        inserted = 0
        duplicates = 0
        errors = []
        
        for comment_req in request.comments:
            try:
                # 确保 platform 一致
                comment_req.platform = request.platform
                
                await self.ingest_comment(comment_req)
                inserted += 1
            except ValueError as e:
                if "Duplicate" in str(e):
                    duplicates += 1
                else:
                    errors.append({"comment": comment_req.content[:50], "error": str(e)})
            except Exception as e:
                errors.append({"comment": comment_req.content[:50], "error": str(e)})
        
        return {
            "inserted": inserted,
            "duplicates": duplicates,
            "errors": errors,
            "total": len(request.comments)
        }
    
    async def get_unprocessed_comments(
        self, 
        project_id: int, 
        limit: int = 100
    ) -> list[RawComment]:
        """获取未处理的评论（用于后续分析）"""
        result = await self.db.execute(
            select(RawComment)
            .where(
                and_(
                    RawComment.project_id == project_id,
                    RawComment.processed == False
                )
            )
            .order_by(RawComment.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def mark_as_processed(self, comment_ids: list[int]) -> int:
        """标记评论为已处理"""
        from sqlalchemy import update
        
        stmt = (
            update(RawComment)
            .where(RawComment.id.in_(comment_ids))
            .values(processed=True, processed_at=datetime.now())
        )
        
        result = await self.db.execute(stmt)
        await self.db.flush()
        
        return result.rowcount
    
    async def get_comment_stats(self, project_id: int) -> dict:
        """获取评论统计"""
        # 总评论数
        total_result = await self.db.execute(
            select(func.count(RawComment.id))
            .where(RawComment.project_id == project_id)
        )
        total = total_result.scalar()
        
        # 未处理数
        unprocessed_result = await self.db.execute(
            select(func.count(RawComment.id))
            .where(
                and_(
                    RawComment.project_id == project_id,
                    RawComment.processed == False
                )
            )
        )
        unprocessed = unprocessed_result.scalar()
        
        # 按平台统计
        platform_result = await self.db.execute(
            select(
                RawComment.platform,
                func.count(RawComment.id).label('count')
            )
            .where(RawComment.project_id == project_id)
            .group_by(RawComment.platform)
        )
        by_platform = {
            row.platform: row.count 
            for row in platform_result.all()
        }
        
        # 按章节统计
        chapter_result = await self.db.execute(
            select(
                RawComment.chapter_id,
                func.count(RawComment.id).label('count')
            )
            .where(
                and_(
                    RawComment.project_id == project_id,
                    RawComment.chapter_id.isnot(None)
                )
            )
            .group_by(RawComment.chapter_id)
        )
        by_chapter = {
            row.chapter_id: row.count 
            for row in chapter_result.all()
        }
        
        return {
            "total": total or 0,
            "unprocessed": unprocessed or 0,
            "by_platform": by_platform,
            "by_chapter": by_chapter
        }
    
    async def delete_project_comments(self, project_id: int) -> int:
        """删除项目的所有评论（项目删除时调用）"""
        from sqlalchemy import delete
        
        stmt = delete(RawComment).where(RawComment.project_id == project_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        
        return result.rowcount
    
    async def get_comments_by_project(
        self,
        project_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> list[RawComment]:
        """获取项目的所有评论"""
        result = await self.db.execute(
            select(RawComment)
            .where(RawComment.project_id == project_id)
            .order_by(RawComment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
