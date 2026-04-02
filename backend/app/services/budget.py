"""调用额度追踪器 - v2.3

控制 LLM 调用频率：
- 300 次/小时全局限制
- 5-7 次调用/章
"""
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta


@dataclass
class ChapterBudget:
    """章节预算"""
    chapter_id: int
    project_id: int
    calls: int = 0
    last_call: Optional[float] = None
    max_calls: int = 7  # 5-7 次/章
    
    def can_call(self) -> bool:
        """检查是否可以调用"""
        return self.calls < self.max_calls
    
    def record_call(self) -> None:
        """记录调用"""
        self.calls += 1
        self.last_call = time.time()
    
    def reset(self) -> None:
        """重置预算"""
        self.calls = 0
        self.last_call = None


@dataclass
class GlobalBudget:
    """全局预算"""
    hourly_limit: int = 300  # 300 次/小时
    _calls: list[float] = field(default_factory=list)
    
    def can_call(self) -> bool:
        """检查是否可以调用"""
        self._cleanup_old_calls()
        return len(self._calls) < self.hourly_limit
    
    def record_call(self) -> None:
        """记录调用"""
        self._cleanup_old_calls()
        self._calls.append(time.time())
    
    def _cleanup_old_calls(self) -> None:
        """清理一小时前的调用记录"""
        cutoff = time.time() - 3600
        self._calls = [t for t in self._calls if t > cutoff]
    
    def get_remaining(self) -> int:
        """获取剩余调用次数"""
        self._cleanup_old_calls()
        return self.hourly_limit - len(self._calls)


class CallBudgetTracker:
    """调用额度追踪器 - v2.3
    
    用法:
        tracker = CallBudgetTracker()
        
        # 检查是否可以调用
        if tracker.can_generate(project_id, chapter_id):
            tracker.record_generate(project_id, chapter_id)
            # 执行生成...
    """
    
    def __init__(
        self,
        hourly_limit: int = 300,
        max_calls_per_chapter: int = 7
    ):
        self.hourly_limit = hourly_limit
        self.max_calls_per_chapter = max_calls_per_chapter
        
        # 全局预算
        self.global_budget = GlobalBudget(hourly_limit=hourly_limit)
        
        # 章节预算: (project_id, chapter_id) -> ChapterBudget
        self._chapter_budgets: dict[tuple[int, int], ChapterBudget] = {}
        
        # 项目维度: project_id -> 已使用调用数
        self._project_calls: dict[int, int] = defaultdict(int)
    
    def _get_chapter_key(self, project_id: int, chapter_id: int) -> tuple[int, int]:
        """获取章节 key"""
        return (project_id, chapter_id)
    
    def _get_chapter_budget(
        self, 
        project_id: int, 
        chapter_id: int
    ) -> ChapterBudget:
        """获取章节预算"""
        key = self._get_chapter_key(project_id, chapter_id)
        if key not in self._chapter_budgets:
            self._chapter_budgets[key] = ChapterBudget(
                chapter_id=chapter_id,
                project_id=project_id,
                max_calls=self.max_calls_per_chapter
            )
        return self._chapter_budgets[key]
    
    def can_generate(
        self, 
        project_id: int, 
        chapter_id: int
    ) -> bool:
        """
        检查是否可以生成
        
        同时检查：
        - 全局 300 次/小时限制
        - 单章节 5-7 次限制
        """
        # 检查全局限制
        if not self.global_budget.can_call():
            return False
        
        # 检查章节限制
        chapter_budget = self._get_chapter_budget(project_id, chapter_id)
        return chapter_budget.can_call()
    
    def record_generate(
        self, 
        project_id: int, 
        chapter_id: int
    ) -> None:
        """记录生成调用"""
        # 记录全局
        self.global_budget.record_call()
        
        # 记录章节
        chapter_budget = self._get_chapter_budget(project_id, chapter_id)
        chapter_budget.record_call()
        
        # 记录项目
        self._project_calls[project_id] += 1
    
    def can_review(
        self, 
        project_id: int, 
        chapter_id: int
    ) -> bool:
        """检查是否可以审查"""
        # 审查调用也计入全局限制
        return self.global_budget.can_call()
    
    def record_review(
        self, 
        project_id: int, 
        chapter_id: int
    ) -> None:
        """记录审查调用"""
        self.global_budget.record_call()
    
    def get_chapter_status(
        self, 
        project_id: int, 
        chapter_id: int
    ) -> dict:
        """获取章节调用状态"""
        budget = self._get_chapter_budget(project_id, chapter_id)
        return {
            "chapter_id": chapter_id,
            "project_id": project_id,
            "calls_used": budget.calls,
            "calls_remaining": budget.max_calls - budget.calls,
            "max_calls": budget.max_calls,
            "can_generate": budget.can_call()
        }
    
    def get_global_status(self) -> dict:
        """获取全局状态"""
        return {
            "hourly_limit": self.hourly_limit,
            "calls_used": len(self.global_budget._calls),
            "calls_remaining": self.global_budget.get_remaining(),
            "reset_in_seconds": 3600 - (time.time() - self.global_budget._calls[-1]) 
                if self.global_budget._calls else 0
        }
    
    def get_project_status(self, project_id: int) -> dict:
        """获取项目状态"""
        # 统计该项目相关的章节调用
        project_chapters = [
            budget for (p, c), budget in self._chapter_budgets.items() 
            if p == project_id
        ]
        
        total_calls = sum(b.calls for b in project_chapters)
        
        return {
            "project_id": project_id,
            "total_calls": total_calls,
            "chapter_count": len(project_chapters)
        }
    
    def reset_chapter(
        self, 
        project_id: int, 
        chapter_id: int
    ) -> None:
        """重置章节预算"""
        key = self._get_chapter_key(project_id, chapter_id)
        if key in self._chapter_budgets:
            self._chapter_budgets[key].reset()
    
    def cleanup_old_entries(self, max_age_hours: int = 24) -> None:
        """清理旧的章节预算记录"""
        cutoff = time.time() - (max_age_hours * 3600)
        keys_to_remove = []
        
        for key, budget in self._chapter_budgets.items():
            if budget.last_call and budget.last_call < cutoff:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._chapter_budgets[key]


# 全局单例
_budget_tracker: Optional[CallBudgetTracker] = None


def get_budget_tracker() -> CallBudgetTracker:
    """获取全局额度追踪器"""
    global _budget_tracker
    if _budget_tracker is None:
        _budget_tracker = CallBudgetTracker()
    return _budget_tracker
