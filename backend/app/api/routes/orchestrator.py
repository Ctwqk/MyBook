"""
Orchestrator API 路由 - v2.3

提供：
- 运行时模式切换
- 任务管理
- 检查点控制
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging

from app.services.orchestrator.schemas import OperationMode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


class SetModeRequest(BaseModel):
    """设置运行模式请求"""
    mode: OperationMode


class ModeResponse(BaseModel):
    """模式响应"""
    current_mode: str
    mode_description: str
    checkpoint_enabled: bool
    auto_retry_enabled: bool


class ModeSwitchResponse(BaseModel):
    """模式切换响应"""
    success: bool
    old_mode: str
    new_mode: str
    timestamp: str


class TaskApprovalRequest(BaseModel):
    """任务审批请求"""
    task_id: str
    decision: str  # proceed, skip, reject


# 全局 orchestrator 服务实例（实际应该通过依赖注入）
_orchestrator_instances: dict[int, any] = {}


def get_orchestrator(project_id: int):
    """获取项目的 orchestrator 实例"""
    # 实际实现应该使用依赖注入或工厂模式
    return _orchestrator_instances.get(project_id)


@router.get("/mode", response_model=ModeResponse)
async def get_mode(project_id: int):
    """
    获取当前运行模式
    
    返回当前的操作模式及其描述
    """
    orchestrator = get_orchestrator(project_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Orchestrator not found for project")
    
    return await orchestrator.get_operation_mode_info()


@router.post("/mode", response_model=ModeSwitchResponse)
async def set_mode(project_id: int, request: SetModeRequest):
    """
    切换运行模式
    
    支持：
    - blackbox: 完全黑箱，无需人工
    - checkpoint: 检查点模式，关键节点等待确认
    - collaborative: 共驾编辑模式
    """
    orchestrator = get_orchestrator(project_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Orchestrator not found for project")
    
    result = await orchestrator.set_operation_mode(request.mode)
    return result


@router.get("/pending-decisions/{project_id}")
async def get_pending_decisions(project_id: int):
    """
    获取待处理的人工决策
    
    返回需要人工介入的任务列表
    """
    orchestrator = get_orchestrator(project_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Orchestrator not found for project")
    
    tasks = await orchestrator.get_pending_human_decisions(project_id)
    
    return {
        "pending_tasks": [
            {
                "task_id": t.task_id,
                "task_type": t.task_type,
                "chapter_id": t.chapter_id,
                "error_message": t.error_message,
                "retry_count": t.retry_count
            }
            for t in tasks
        ],
        "count": len(tasks)
    }


@router.post("/approve-task")
async def approve_task(request: TaskApprovalRequest):
    """
    审批任务
    
    decision 选项：
    - proceed: 继续执行
    - skip: 跳过此任务
    - reject: 拒绝并标记失败
    """
    # 遍历所有项目的 orchestrator 查找任务
    for orchestrator in _orchestrator_instances.values():
        result = await orchestrator.approve_task(request.task_id, request.decision)
        if result.get("success"):
            return result
    
    raise HTTPException(status_code=404, detail="Task not found")


@router.post("/checkpoint/{task_id}/resume")
async def resume_from_checkpoint(task_id: str):
    """
    从检查点恢复任务执行
    
    人工确认后调用此接口继续执行
    """
    for orchestrator in _orchestrator_instances.values():
        # 查找任务并恢复
        for project_tasks in orchestrator._task_queue.values():
            for task in project_tasks:
                if task.task_id == task_id:
                    task.status = "pending"  # 恢复执行
                    return {"success": True, "task_id": task_id, "status": "resumed"}
    
    raise HTTPException(status_code=404, detail="Task not found")


def register_orchestrator(project_id: int, orchestrator):
    """注册项目的 orchestrator 实例"""
    _orchestrator_instances[project_id] = orchestrator


def unregister_orchestrator(project_id: int):
    """注销项目的 orchestrator 实例"""
    if project_id in _orchestrator_instances:
        del _orchestrator_instances[project_id]
