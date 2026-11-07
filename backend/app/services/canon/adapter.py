"""DeltaAdapter - 统一 Delta 提交接口

将各类来源的变更统一适配到 GraphDelta 系统
"""
from dataclasses import dataclass
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.graph_deltas import GraphDelta, DeltaType, SourceType
from app.services.book_state import GraphDeltaCompiler, PatchResult


@dataclass
class DeltaRequest:
    """Delta 请求"""
    project_id: int
    chapter_number: Optional[int]
    source_type: str
    source_id: Optional[str]
    summary: str
    node_patches: list[dict]
    edge_patches: list[dict]


@dataclass
class DeltaResult:
    """Delta 结果"""
    success: bool
    delta_id: Optional[int]
    patch_results: list[PatchResult]
    error: Optional[str] = None


class DeltaAdapter:
    """
    统一 Delta 提交适配器
    
    接收各类来源的变更请求，统一转换为 GraphDelta 格式：
    - Writer: 章节写作产生的变更
    - Reviewer: 审阅产生的修正
    - ArcPlanner: Arc 规划产生的变更
    - Manual: 手动编辑
    - Import: 从外部导入
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.compiler = GraphDeltaCompiler(db)
    
    async def submit_delta(self, request: DeltaRequest) -> DeltaResult:
        """
        提交一个 Delta
        
        流程：
        1. 验证请求
        2. 调用编译器编译 patches
        3. 返回结果
        """
        try:
            source_type = SourceType(request.source_type)
        except ValueError:
            return DeltaResult(
                success=False,
                delta_id=None,
                patch_results=[],
                error=f"Invalid source_type: {request.source_type}"
            )
        
        result = await self.compiler.compile(
            project_id=request.project_id,
            chapter_number=request.chapter_number,
            node_patches=request.node_patches,
            edge_patches=request.edge_patches,
            source_type=source_type,
            source_id=request.source_id,
            summary=request.summary
        )
        
        return DeltaResult(
            success=result.success,
            delta_id=result.delta.id if result.delta else None,
            patch_results=result.patch_results,
            error="; ".join(result.errors) if result.errors else None
        )
    
    async def submit_writer_delta(
        self,
        project_id: int,
        chapter_number: int,
        node_patches: list[dict],
        edge_patches: list[dict],
        summary: str,
        source_id: Optional[str] = None
    ) -> DeltaResult:
        """提交 Writer 产生的 Delta"""
        return await self.submit_delta(DeltaRequest(
            project_id=project_id,
            chapter_number=chapter_number,
            source_type="writer",
            source_id=source_id or f"writer_chapter_{chapter_number}",
            summary=summary,
            node_patches=node_patches,
            edge_patches=edge_patches
        ))
    
    async def submit_reviewer_delta(
        self,
        project_id: int,
        chapter_number: int,
        node_patches: list[dict],
        edge_patches: list[dict],
        summary: str,
        source_id: Optional[str] = None
    ) -> DeltaResult:
        """提交 Reviewer 产生的 Delta"""
        return await self.submit_delta(DeltaRequest(
            project_id=project_id,
            chapter_number=chapter_number,
            source_type="reviewer",
            source_id=source_id or f"reviewer_chapter_{chapter_number}",
            summary=summary,
            node_patches=node_patches,
            edge_patches=edge_patches
        ))
    
    async def submit_manual_delta(
        self,
        project_id: int,
        node_patches: list[dict],
        edge_patches: list[dict],
        summary: str,
        chapter_number: Optional[int] = None
    ) -> DeltaResult:
        """提交手动编辑的 Delta"""
        return await self.submit_delta(DeltaRequest(
            project_id=project_id,
            chapter_number=chapter_number,
            source_type="manual",
            source_id="manual_edit",
            summary=summary,
            node_patches=node_patches,
            edge_patches=edge_patches
        ))
    
    async def submit_arc_delta(
        self,
        project_id: int,
        arc_id: str,
        node_patches: list[dict],
        edge_patches: list[dict],
        summary: str,
        chapter_start: int,
        chapter_end: int
    ) -> DeltaResult:
        """提交 Arc 规划产生的 Delta"""
        return await self.submit_delta(DeltaRequest(
            project_id=project_id,
            chapter_number=chapter_start,  # 使用起始章节
            source_type="arc_planner",
            source_id=f"arc_{arc_id}",
            summary=f"[Arc {arc_id}] {summary}",
            node_patches=node_patches,
            edge_patches=edge_patches
        ))
    
    async def batch_submit_deltas(self, requests: list[DeltaRequest]) -> list[DeltaResult]:
        """批量提交 Deltas"""
        results = []
        for request in requests:
            result = await self.submit_delta(request)
            results.append(result)
        return results
    
    async def revert_delta(self, delta_id: int) -> bool:
        """
        回滚一个 Delta
        
        实现方式：
        1. 获取原始 delta
        2. 生成反向 patches
        3. 提交反向 delta
        """
        from sqlalchemy import select
        
        result = await self.db.execute(
            select(GraphDelta).where(GraphDelta.id == delta_id)
        )
        delta = result.scalar_one_or_none()
        
        if not delta or delta.is_reverted:
            return False
        
        # 生成反向 patches
        node_patches = []
        edge_patches = []
        
        # TODO: 根据 delta.content_json 生成反向 patches
        
        # 提交反向 delta
        reverse_result = await self.submit_delta(DeltaRequest(
            project_id=delta.project_id,
            chapter_number=delta.chapter_number,
            source_type="revert",
            source_id=f"revert_{delta_id}",
            summary=f"Revert delta {delta_id}: {delta.summary}",
            node_patches=node_patches,
            edge_patches=edge_patches
        ))
        
        if reverse_result.success:
            delta.is_reverted = True
            await self.db.flush()
        
        return reverse_result.success
