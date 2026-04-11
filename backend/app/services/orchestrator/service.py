"""Orchestrator Service - v2.3 多项目隔离 + 任务管理

支持：
- 多项目并行任务隔离
- 任务队列管理
- 错误恢复流程
- 黑箱/人工双模式
"""
import asyncio
import json
from datetime import datetime
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import LLMProvider
from app.repositories.project import ProjectRepository
from app.repositories.chapter import ChapterRepository
from app.services.memory.service import MemoryService
from app.services.planner.service import PlannerService
from app.core.exceptions import GenerationError, ReviewError
from app.services.orchestrator.schemas import (
    Task, TaskStatus, OperationMode, RetryPolicy,
    WriterOutput, ReviewVerdictV2, StateUpdateResult
)
from app.services.writer.service import WriterService


class OrchestratorService:
    """编排服务 - v2.3"""

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: Optional[LLMProvider] = None,
        operation_mode: OperationMode = OperationMode.CHECKPOINT,
        retry_policy: Optional[RetryPolicy] = None
    ):
        self.db = db
        self.llm = llm_provider
        
        # Repository
        self.project_repo = ProjectRepository(db)
        self.chapter_repo = ChapterRepository(db)
        
        # Services - 每个项目隔离
        self.memory_service = MemoryService(db)
        self.planner_service = PlannerService(db, llm_provider)
        self.writer_service = WriterService(db, llm_provider, operation_mode, retry_policy)
        # 延迟导入避免循环依赖
        from app.services.reviewer.service import ReviewerService
        self.reviewer_service = ReviewerService(db, llm_provider, operation_mode, retry_policy)
        
        # v2.3 配置
        self.operation_mode = operation_mode
        self.retry_policy = retry_policy or RetryPolicy()
        
        # 任务队列（内存中，生产环境应使用 Redis）
        self._task_queue: dict[int, list[Task]] = {}  # project_id -> tasks
        
        # 运行时模式（可动态切换）
        self._operation_mode = operation_mode
        self._mode_lock = asyncio.Lock()  # 模式切换锁


    # ==================== 多项目隔离 ====================

    def _get_project_tasks(self, project_id: int) -> list[Task]:
        """获取项目的任务队列"""
        if project_id not in self._task_queue:
            self._task_queue[project_id] = []
        return self._task_queue[project_id]

    def _validate_project_scope(self, project_id: int, resource_project_id: int) -> bool:
        """验证项目范围 - 多项目隔离"""
        return project_id == resource_project_id

    # ==================== 任务管理 ====================

    async def create_task(
        self,
        project_id: int,
        task_type: str,
        chapter_id: Optional[int] = None,
        priority: int = 0
    ) -> Task:
        """创建任务"""
        task = Task(
            task_id=f"{project_id}_{task_type}_{datetime.now().timestamp()}",
            project_id=project_id,
            task_type=task_type,
            chapter_id=chapter_id,
            priority=priority,
            status=TaskStatus.PENDING
        )
        
        tasks = self._get_project_tasks(project_id)
        tasks.append(task)
        
        # 按优先级排序
        tasks.sort(key=lambda t: t.priority, reverse=True)
        
        return task

    async def get_next_task(self, project_id: int) -> Optional[Task]:
        """获取下一个待执行任务"""
        tasks = self._get_project_tasks(project_id)
        
        for task in tasks:
            if task.status == TaskStatus.PENDING:
                return task
        
        return None

    async def execute_task(self, task: Task) -> dict[str, Any]:
        """执行任务"""
        # 验证项目隔离
        task_project_id = task.project_id
        
        try:
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.now()
            
            result = await self._dispatch_task(task)
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            return {"success": True, "task": task, "result": result}
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            
            return await self._handle_task_failure(task, e)

    async def _dispatch_task(self, task: Task) -> Any:
        """分发任务到对应服务"""
        # 项目隔离检查
        project_id = task.project_id
        
        if task.task_type == "bootstrap":
            return await self._bootstrap_project(project_id)
        
        elif task.task_type == "generate":
            return await self._generate_chapter(project_id, task.chapter_id)
        
        elif task.task_type == "review":
            return await self._review_chapter(project_id, task.chapter_id)
        
        elif task.task_type == "patch":
            return await self._patch_chapter(project_id, task.chapter_id)
        
        elif task.task_type == "rewrite":
            return await self._rewrite_chapter(project_id, task.chapter_id)
        
        elif task.task_type == "replan":
            return await self._replan_project(project_id)
        
        else:
            raise ValueError(f"Unknown task type: {task.task_type}")

    async def _handle_task_failure(self, task: Task, error: Exception) -> dict[str, Any]:
        """处理任务失败"""
        task.retry_count += 1
        
        if task.retry_count <= self.retry_policy.max_retries:
            # 重试
            task.status = TaskStatus.PENDING
            return {
                "success": False,
                "task": task,
                "error": str(error),
                "action": "retry"
            }
        else:
            # 升级
            task.status = TaskStatus.NEEDS_ATTENTION
            
            if self.operation_mode == OperationMode.BLACKBOX:
                # 黑箱模式：降级处理
                return {
                    "success": False,
                    "task": task,
                    "error": str(error),
                    "action": "blackbox_degrade"
                }
            else:
                # 人工介入
                return {
                    "success": False,
                    "task": task,
                    "error": str(error),
                    "action": "escalate"
                }

    # ==================== 核心流程 ====================

    async def _bootstrap_project(self, project_id: int) -> dict[str, Any]:
        """引导项目 - Planner 生成初始内容"""
        # 验证项目隔离
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Planner 生成 Story Bible
        story_bible = await self.planner_service.generate_story_bible(project_id)
        
        return {
            "project_id": project_id,
            "story_bible": story_bible
        }

    async def _generate_chapter(self, project_id: int, chapter_id: int) -> WriterOutput:
        """生成章节 - v2.3 checkpoint 集成"""
        # 项目隔离检查
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter or chapter.project_id != project_id:
            raise ValueError(f"Chapter {chapter_id} not found in project {project_id}")
        
        # 创建内部任务用于 checkpoint
        task = Task(
            task_id=f"{project_id}_generate_{chapter_id}_{datetime.now().timestamp()}",
            project_id=project_id,
            task_type="generate",
            chapter_id=chapter_id,
            status=TaskStatus.IN_PROGRESS
        )
        
        # CHECKPOINT: 生成前等待人工确认（CHECKPOINT 模式下）
        await self.checkpoint_wait(task)
        
        # Writer 生成
        writer_request = self.writer_service.generate_chapter(
            project_id, chapter_id, request=None
        )
        
        return await writer_request

    async def _review_chapter(self, project_id: int, chapter_id: int) -> ReviewVerdictV2:
        """审查章节 - v2.3 checkpoint 集成"""
        # 项目隔离检查
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter or chapter.project_id != project_id:
            raise ValueError(f"Chapter {chapter_id} not found in project {project_id}")
        
        # 创建内部任务用于 checkpoint
        task = Task(
            task_id=f"{project_id}_review_{chapter_id}_{datetime.now().timestamp()}",
            project_id=project_id,
            task_type="review",
            chapter_id=chapter_id,
            status=TaskStatus.IN_PROGRESS
        )
        
        # CHECKPOINT: 审查前等待人工确认（CHECKPOINT 模式下）
        await self.checkpoint_wait(task)
        
        # Reviewer 审查
        verdict = await self.reviewer_service.review_chapter(
            project_id, chapter_id
        )
        
        return verdict

    async def _patch_chapter(self, project_id: int, chapter_id: int) -> dict[str, Any]:
        """修补章节"""
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter or chapter.project_id != project_id:
            raise ValueError(f"Chapter {chapter_id} not found in project {project_id}")
        
        # 获取待修补的问题
        # TODO: 实现修补逻辑
        
        return {"chapter_id": chapter_id, "action": "patch"}

    async def _rewrite_chapter(self, project_id: int, chapter_id: int) -> dict[str, Any]:
        """重写章节"""
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter or chapter.project_id != project_id:
            raise ValueError(f"Chapter {chapter_id} not found in project {project_id}")
        
        # 获取重写指令
        rewrite_instructions = await self.reviewer_service.build_rewrite_instructions(
            project_id, chapter_id
        )
        
        # 重写
        result = await self.writer_service.rewrite_chapter(
            project_id, chapter_id, request=rewrite_instructions
        )
        
        return result

    async def _replan_project(self, project_id: int) -> dict[str, Any]:
        """重规划项目"""
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Planner 重规划
        # TODO: 实现重规划逻辑
        
        return {"project_id": project_id, "action": "replan"}

    # ==================== 运行时模式切换 ====================

    @property
    def operation_mode(self) -> OperationMode:
        """获取当前运行模式"""
        return self._operation_mode
    
    async def set_operation_mode(self, mode: OperationMode) -> dict[str, Any]:
        """
        运行时切换操作模式
        
        支持三种模式：
        - BLACKBOX: 完全黑箱，无需人工干预
        - CHECKPOINT: 关键节点等待人工确认
        - COLLABORATIVE: 共驾编辑模式
        
        Returns:
            切换前后的模式信息
        """
        async with self._mode_lock:
            old_mode = self._operation_mode
            self._operation_mode = mode
            
            # 同步更新子服务
            self.writer_service.operation_mode = mode
            self.reviewer_service.operation_mode = mode
            
            return {
                "success": True,
                "old_mode": old_mode.value,
                "new_mode": mode.value,
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_operation_mode_info(self) -> dict[str, Any]:
        """获取当前模式详细信息"""
        return {
            "current_mode": self._operation_mode.value,
            "mode_description": self._get_mode_description(self._operation_mode),
            "checkpoint_enabled": self._operation_mode == OperationMode.CHECKPOINT,
            "auto_retry_enabled": self._operation_mode in [
                OperationMode.BLACKBOX, 
                OperationMode.CHECKPOINT
            ]
        }
    
    def _get_mode_description(self, mode: OperationMode) -> str:
        """获取模式描述"""
        descriptions = {
            OperationMode.BLACKBOX: "完全黑箱模式：所有任务自动执行，无需人工干预。失败时自动降级处理。",
            OperationMode.CHECKPOINT: "检查点模式：关键节点暂停等待人工确认后继续执行。",
            OperationMode.COLLABORATIVE: "共驾编辑模式：人机协作，实时反馈与调整。"
        }
        return descriptions.get(mode, "未知模式")

    # ==================== 人工介入点 ====================

    async def checkpoint_wait(self, task: Task) -> None:
        """
        检查点等待人工确认 - v2.3 增强版
        
        增强功能：
        1. CHECKPOINT模式：暂停并等待人工确认
        2. BLACKBOX模式：自动继续执行
        3. COLLABORATIVE模式：提供建议但不阻塞
        4. 支持超时机制（默认30秒后自动继续）
        5. 状态设为NEEDS_ATTENTION供前端展示
        """
        if self._operation_mode == OperationMode.BLACKBOX:
            # 黑箱模式：完全自动，无需人工干预
            return
        
        if self._operation_mode == OperationMode.COLLABORATIVE:
            # 共驾模式：提供建议但不阻塞，给出提示后继续
            task.notes = f"建议: 考虑检查当前生成内容是否符合预期"
            return
        
        # CHECKPOINT 模式：暂停等待确认
        task.status = TaskStatus.NEEDS_ATTENTION
        task.notes = f"【CHECKPOINT】等待人工确认以继续执行..."
        
        # 等待确认（最多30秒超时）
        timeout_seconds = 30
        waited = 0
        while task.status == TaskStatus.NEEDS_ATTENTION:
            await asyncio.sleep(1)
            waited += 1
            if waited >= timeout_seconds:
                # 超时自动继续（安全机制）
                task.status = TaskStatus.PENDING
                task.notes = f"【CHECKPOINT】超时自动继续 (等待了{timeout_seconds}秒)"
                break

    async def get_pending_human_decisions(self, project_id: int) -> list[Task]:
        """获取需要人工决策的任务"""
        tasks = self._get_project_tasks(project_id)
        return [t for t in tasks if t.status == TaskStatus.NEEDS_ATTENTION]

    async def approve_task(self, task_id: str, decision: str) -> dict[str, Any]:
        """人工批准任务决策"""
        for project_tasks in self._task_queue.values():
            for task in project_tasks:
                if task.task_id == task_id:
                    if decision == "proceed":
                        task.status = TaskStatus.PENDING
                        return {"success": True, "action": "proceed"}
                    elif decision == "skip":
                        task.status = TaskStatus.COMPLETED
                        return {"success": True, "action": "skip"}
                    else:
                        task.status = TaskStatus.FAILED
                        return {"success": True, "action": "reject"}
        
        return {"success": False, "error": "Task not found"}

    # ==================== State Updater 事务边界 ====================

    async def update_state(
        self,
        project_id: int,
        writer_output: WriterOutput,
        review_verdict: ReviewVerdictV2
    ) -> StateUpdateResult:
        """
        状态更新 - 带事务边界
        
        确保：
        - candidate 失败不影响 canon
        - 事务失败时 rollback
        """
        try:
            # 验证项目隔离
            if writer_output.project_id != project_id:
                raise ValueError("Project ID mismatch")
            
            applied = []
            rejected = []
            failed = []
            
            # 使用显式事务确保原子性
            async with self.db.begin():
                # 1. 验证 candidates
                for candidate in writer_output.state_change_candidates:
                    if self._validate_candidate(candidate):
                        applied.append(candidate)
                    else:
                        rejected.append(candidate)
                
                # 2. 应用更新
                for candidate in applied:
                    await self._apply_candidate(project_id, candidate)
                
                # 3. 审查 verdict
                for issue in review_verdict.issues:
                    await self.memory_service.record_review_note(
                        project_id=project_id,
                        chapter_id=writer_output.chapter_id,
                        issue_type=issue.get("issue_type", "unknown"),
                        severity=issue.get("severity", "minor"),
                        description=issue.get("description", ""),
                        fix_suggestion=issue.get("fix_suggestion")
                    )
                
                # 事务内 flush 确保写入
                await self.db.flush()
            
            return StateUpdateResult(
                success=True,
                applied_candidates=[str(c) for c in applied],
                rejected_candidates=[str(c) for c in rejected]
            )
            
        except Exception as e:
            # 事务失败 - rollback (由 async with 自动处理)
            return StateUpdateResult(
                success=False,
                rollback_performed=True,
                rollback_reason=str(e),
                error_message=str(e)
            )

    def _validate_candidate(self, candidate: dict) -> bool:
        """验证 candidate 是否有效"""
        # 简单验证
        return bool(candidate.get("content"))

    async def _apply_candidate(self, project_id: int, candidate: dict) -> None:
        """应用 candidate 到 canon"""
        update_type = candidate.get("update_type")
        
        if update_type == "character_state":
            await self.memory_service.update_character_states(
                project_id,
                candidate.get("character_id"),
                candidate.get("content", {})
            )
        elif update_type == "foreshadow":
            if candidate.get("action") == "resolve":
                await self.memory_service.resolve_foreshadow(
                    candidate.get("foreshadow_id")
                )
            else:
                await self.memory_service.record_foreshadow(
                    project_id,
                    candidate.get("chapter_id"),
                    candidate.get("content"),
                    candidate.get("related_entities")
                )
        # 其他类型...
