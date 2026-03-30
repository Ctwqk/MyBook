"""Publish State Machine - 发布状态机"""
from typing import Set
from app.models.publish_task import PublishStatus


class PublishStateMachine:
    """发布任务状态机"""
    
    # 允许的状态转换
    TRANSITIONS: dict[PublishStatus, Set[PublishStatus]] = {
        PublishStatus.PENDING: {
            PublishStatus.PREPARING,
            PublishStatus.CANCELLED,
            PublishStatus.FAILED,
        },
        PublishStatus.PREPARING: {
            PublishStatus.SUBMITTING,
            PublishStatus.FAILED,
            PublishStatus.CANCELLED,
        },
        PublishStatus.SUBMITTING: {
            PublishStatus.SUCCESS,
            PublishStatus.FAILED,
        },
        PublishStatus.SUCCESS: set(),  # 终态
        PublishStatus.FAILED: {
            PublishStatus.PENDING,  # 可以重试
        },
        PublishStatus.CANCELLED: set(),  # 终态
    }
    
    def can_transition(self, from_status: PublishStatus, to_status: PublishStatus) -> bool:
        """检查是否允许状态转换"""
        allowed = self.TRANSITIONS.get(from_status, set())
        return to_status in allowed
    
    def can_cancel(self, status: PublishStatus) -> bool:
        """检查是否可以取消"""
        return status in {PublishStatus.PENDING, PublishStatus.PREPARING}
    
    def can_retry(self, status: PublishStatus) -> bool:
        """检查是否可以重试"""
        return status == PublishStatus.FAILED
    
    def is_terminal(self, status: PublishStatus) -> bool:
        """检查是否是终态"""
        return status in {PublishStatus.SUCCESS, PublishStatus.CANCELLED}
    
    def get_next_status(self, current: PublishStatus) -> PublishStatus:
        """获取下一个默认状态"""
        transitions = {
            PublishStatus.PENDING: PublishStatus.PREPARING,
            PublishStatus.PREPARING: PublishStatus.SUBMITTING,
            PublishStatus.SUBMITTING: PublishStatus.SUCCESS,
        }
        return transitions.get(current, current)
