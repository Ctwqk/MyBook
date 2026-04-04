"""Feedback Cooldown Service - v2.6

职责：
- 管理反馈响应冷却期
- 防止同一信号类型的重复响应
- 记录动作响应历史
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, select, and_
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FeedbackActionRecord(Base):
    """反馈动作记录 - 用于冷却期管理"""
    __tablename__ = "feedback_action_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # 信号键（用于识别同类型信号）
    signal_key = Column(String(100), nullable=False, index=True)
    
    # 动作类型
    action_type = Column(String(50), nullable=False)
    
    # 章节信息
    chapter_number = Column(Integer, nullable=False)
    
    # 冷却期截止章节
    cooldown_until = Column(Integer, nullable=False, index=True)
    
    # 响应详情
    response_summary = Column(Text, nullable=True)
    
    # 元数据
    created_at = Column(DateTime, default=datetime.now)
    
    # 复合索引
    __table_args__ = (
        Index('idx_project_signal', 'project_id', 'signal_key'),
        Index('idx_cooldown_lookup', 'project_id', 'cooldown_until'),
    )
    
    def __repr__(self):
        return f"<FeedbackActionRecord id={self.id} signal_key={self.signal_key} chapter={self.chapter_number}>"


class FeedbackCooldown:
    """
    反馈冷却期管理 - v2.6
    
    核心功能：
    1. 检查特定信号键是否在冷却期内
    2. 记录响应动作并设置冷却期
    3. 防止对同一信号类型的过度响应
    """
    
    def __init__(self, cooldown_chapters: int = 3):
        """
        初始化冷却期管理器
        
        Args:
            cooldown_chapters: 冷却期章节数，默认为 3 章
        """
        self.cooldown_chapters = cooldown_chapters
    
    async def is_cooled(
        self, 
        session, 
        project_id: int, 
        signal_key: str, 
        chapter_number: int
    ) -> bool:
        """
        检查是否在冷却期内
        
        Args:
            session: 数据库会话（AsyncSession）
            project_id: 项目 ID
            signal_key: 信号键（如 "confusion:character:1"）
            chapter_number: 当前章节号
            
        Returns:
            True if cooled (in cooldown period), False if can respond
        """
        # 查询最近一次该 signal_key 的响应记录
        result = await session.execute(
            select(FeedbackActionRecord)
            .where(
                and_(
                    FeedbackActionRecord.project_id == project_id,
                    FeedbackActionRecord.signal_key == signal_key
                )
            )
            .order_by(FeedbackActionRecord.created_at.desc())
            .limit(1)
        )
        
        last_action = result.scalar_one_or_none()
        
        # 如果没有记录，则不在冷却期内
        if last_action is None:
            return False
        
        # 如果 chapter_number < cooldown_until，返回 True（在冷却期内）
        # 如果 chapter_number >= cooldown_until，返回 False（冷却期已过）
        return chapter_number < last_action.cooldown_until
    
    async def record_action(
        self, 
        session, 
        project_id: int, 
        signal_key: str, 
        action_type: str, 
        chapter_number: int,
        response_summary: Optional[str] = None
    ) -> FeedbackActionRecord:
        """
        记录一次响应动作
        
        Args:
            session: 数据库会话（AsyncSession）
            project_id: 项目 ID
            signal_key: 信号键
            action_type: 动作类型（如 "clarification", "adjustment"）
            chapter_number: 当前章节号
            response_summary: 响应摘要（可选）
            
        Returns:
            新创建的 FeedbackActionRecord
        """
        # 计算冷却期截止章节
        cooldown_until = chapter_number + self.cooldown_chapters
        
        # 创建记录
        record = FeedbackActionRecord(
            project_id=project_id,
            signal_key=signal_key,
            action_type=action_type,
            chapter_number=chapter_number,
            cooldown_until=cooldown_until,
            response_summary=response_summary,
            created_at=datetime.now()
        )
        
        session.add(record)
        await session.flush()
        await session.refresh(record)
        
        return record
    
    async def get_cooldown_remaining(
        self,
        session,
        project_id: int,
        signal_key: str,
        chapter_number: int
    ) -> int:
        """
        获取剩余冷却章节数
        
        Args:
            session: 数据库会话
            project_id: 项目 ID
            signal_key: 信号键
            chapter_number: 当前章节号
            
        Returns:
            剩余冷却章节数，0 表示不在冷却期内
        """
        result = await session.execute(
            select(FeedbackActionRecord)
            .where(
                and_(
                    FeedbackActionRecord.project_id == project_id,
                    FeedbackActionRecord.signal_key == signal_key
                )
            )
            .order_by(FeedbackActionRecord.created_at.desc())
            .limit(1)
        )
        
        last_action = result.scalar_one_or_none()
        
        if last_action is None:
            return 0
        
        remaining = last_action.cooldown_until - chapter_number
        return max(0, remaining)
    
    async def clear_cooldown(
        self,
        session,
        project_id: int,
        signal_key: str
    ) -> bool:
        """
        清除特定信号键的冷却期
        
        Args:
            session: 数据库会话
            project_id: 项目 ID
            signal_key: 信号键
            
        Returns:
            是否成功清除
        """
        from sqlalchemy import delete
        
        result = await session.execute(
            delete(FeedbackActionRecord)
            .where(
                and_(
                    FeedbackActionRecord.project_id == project_id,
                    FeedbackActionRecord.signal_key == signal_key
                )
            )
        )
        
        await session.flush()
        return result.rowcount > 0
