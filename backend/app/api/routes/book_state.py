"""BookState API Routes - 世界状态 API

端点：
- GET  /api/projects/{project_id}/book-state/runtime - 获取当前运行时状态
- GET  /api/projects/{project_id}/book-state/nodes - 获取所有节点
- GET  /api/projects/{project_id}/book-state/edges - 获取所有边
- GET  /api/projects/{project_id}/book-state/deltas - 获取增量记录
- POST /api/projects/{project_id}/book-state/compile - 编译 patches
- GET  /api/projects/{project_id}/book-state/snapshot - 获取快照
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.book_state import BookStateRuntime, GraphDeltaCompiler, BookStateRepository
from app.models.graph_deltas import SourceType
from app.models.world_nodes import WorldNodeType
from app.models.world_edges import EdgeType

router = APIRouter(prefix="/api/projects/{project_id}/book-state", tags=["book-state"])


@router.get("/runtime")
async def get_runtime(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取 BookState 运行时状态"""
    runtime = BookStateRuntime(db, project_id)
    await runtime.load_current_state()
    
    return {
        "project_id": project_id,
        "node_count": await runtime.get_node_count(),
        "edge_count": await runtime.get_edge_count(),
        "characters": [
            {
                "id": node.id,
                "name": node.name,
                "state": node.state_json
            }
            for node in await runtime.get_all_characters()
        ]
    }


@router.get("/nodes")
async def get_nodes(
    project_id: int,
    node_type: Optional[str] = Query(None, description="节点类型筛选"),
    db: AsyncSession = Depends(get_db)
):
    """获取项目的所有节点"""
    repo = BookStateRepository(db)
    
    wnt = None
    if node_type:
        try:
            wnt = WorldNodeType(node_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid node_type: {node_type}")
    
    nodes = await repo.get_nodes_by_project(project_id, node_type=wnt)
    
    return {
        "project_id": project_id,
        "count": len(nodes),
        "nodes": [
            {
                "id": node.id,
                "node_type": node.node_type.value,
                "name": node.name,
                "aliases": node.aliases,
                "description": node.description,
                "importance": node.importance.value,
                "is_active": node.is_active,
                "created_at_chapter": node.created_at_chapter,
                "profile_json": node.profile_json,
                "state_json": node.state_json
            }
            for node in nodes
        ]
    }


@router.get("/edges")
async def get_edges(
    project_id: int,
    edge_type: Optional[str] = Query(None, description="边类型筛选"),
    db: AsyncSession = Depends(get_db)
):
    """获取项目的所有边"""
    repo = BookStateRepository(db)
    
    et = None
    if edge_type:
        try:
            et = EdgeType(edge_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid edge_type: {edge_type}")
    
    edges = await repo.get_edges_by_project(project_id, edge_type=et)
    
    return {
        "project_id": project_id,
        "count": len(edges),
        "edges": [
            {
                "id": edge.id,
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "edge_type": edge.edge_type.value,
                "edge_family": edge.edge_family.value,
                "directionality": edge.directionality.value,
                "weight": edge.weight,
                "confidence": edge.confidence,
                "is_active": edge.is_active
            }
            for edge in edges
        ]
    }


@router.get("/deltas")
async def get_deltas(
    project_id: int,
    up_to_chapter: Optional[int] = Query(None, description="截止章节"),
    db: AsyncSession = Depends(get_db)
):
    """获取增量记录"""
    repo = BookStateRepository(db)
    deltas = await repo.get_deltas_by_project(project_id, up_to_chapter=up_to_chapter)
    
    return {
        "project_id": project_id,
        "count": len(deltas),
        "deltas": [
            {
                "id": delta.id,
                "chapter_number": delta.chapter_number,
                "delta_type": delta.delta_type.value,
                "source_type": delta.source_type.value,
                "summary": delta.summary,
                "is_committed": delta.is_committed,
                "is_reverted": delta.is_reverted,
                "created_at": delta.created_at.isoformat() if delta.created_at else None
            }
            for delta in deltas
        ]
    }


@router.post("/compile")
async def compile_patches(
    project_id: int,
    node_patches: list[dict],
    edge_patches: list[dict],
    chapter_number: Optional[int] = None,
    source_type: str = "writer",
    source_id: Optional[str] = None,
    summary: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    编译 patches 并提交到 GraphDelta
    
    请求体:
    ```json
    {
        "node_patches": [
            {"op": "create", "node_type": "character", "name": "张三", "project_id": 1},
            {"op": "set", "node_id": 1, "field_path": "state_json", "new_value": {"health": 100}}
        ],
        "edge_patches": [
            {"op": "create", "source_id": 1, "target_id": 2, "edge_type": "ally_of", "project_id": 1}
        ],
        "chapter_number": 5,
        "source_type": "writer",
        "source_id": "writer_chapter_5",
        "summary": "角色张三出场，与李四结盟"
    }
    ```
    """
    try:
        st = SourceType(source_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid source_type: {source_type}")
    
    compiler = GraphDeltaCompiler(db)
    result = await compiler.compile(
        project_id=project_id,
        chapter_number=chapter_number,
        node_patches=node_patches,
        edge_patches=edge_patches,
        source_type=st,
        source_id=source_id,
        summary=summary
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail={
            "errors": result.errors,
            "patch_results": [
                {
                    "index": pr.patch_index,
                    "success": pr.success,
                    "error": pr.error
                }
                for pr in result.patch_results
            ]
        })
    
    return {
        "success": True,
        "delta_id": result.delta.id if result.delta else None,
        "patch_results": [
            {
                "index": pr.patch_index,
                "success": pr.success,
                "error": pr.error
            }
            for pr in result.patch_results
        ],
        "warnings": result.errors
    }


@router.get("/snapshot")
async def get_snapshot(
    project_id: int,
    as_of_chapter: int = Query(..., description="获取到此章节的状态"),
    db: AsyncSession = Depends(get_db)
):
    """获取指定章节的世界状态快照"""
    runtime = BookStateRuntime(db, project_id)
    snapshot = await runtime.get_snapshot(as_of_chapter)
    
    return {
        "project_id": project_id,
        "as_of_chapter": snapshot.as_of_chapter,
        "as_of_story_time": snapshot.as_of_story_time,
        "node_count": len(snapshot.world_graph.nodes_by_id),
        "edge_count": len(snapshot.world_graph.edges_by_id),
        "nodes": [
            {
                "id": node.id,
                "node_type": node.node_type.value,
                "name": node.name,
                "is_active": node.is_active
            }
            for node in snapshot.world_graph.nodes_by_id.values()
        ]
    }