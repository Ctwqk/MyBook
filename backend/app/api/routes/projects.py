"""项目相关 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.project import Project, ProjectStatus
from app.repositories.project import ProjectRepository
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)
from app.services.planner.service import PlannerService
from app.services.planner.schemas import (
    ArcPlan,
    ChapterOutline,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建新项目"""
    repo = ProjectRepository(db)
    
    # 检查是否已存在同名项目
    existing = await repo.get_by_title(data.title)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with title '{data.title}' already exists"
        )
    
    project = Project(
        title=data.title,
        genre=data.genre,
        style=data.style,
        premise=data.premise,
        target_length=data.target_length,
        status=ProjectStatus.DRAFT
    )
    
    db.add(project)
    await db.flush()
    await db.refresh(project)
    
    return project


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    skip: int = 0,
    limit: int = 20,
    status: ProjectStatus = None,
    db: AsyncSession = Depends(get_db)
):
    """获取项目列表"""
    repo = ProjectRepository(db)
    
    if status:
        items = await repo.get_by_status(status, skip, limit)
        total = await repo.count_by_status(status)
    else:
        items = await repo.get_all(skip, limit)
        total = await repo.count()
    
    return ProjectListResponse(items=items, total=total)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取项目详情"""
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新项目"""
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    
    await db.flush()
    await db.refresh(project)
    
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除项目"""
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    await db.delete(project)
    await db.flush()


# ==================== 规划相关 API ====================

@router.post("/{project_id}/bootstrap")
async def bootstrap_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    引导项目 - 生成 Story Bible 和初始角色
    
    这是一个便捷端点，会自动：
    1. 解析 premise
    2. 生成 Story Bible
    3. 生成主要角色卡
    """
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    planner = PlannerService(db)
    
    # 解析 premise
    if project.premise:
        await planner.parse_premise(project.premise)
    
    # 生成 Story Bible
    story_bible = await planner.bootstrap_story(
        project_id=project_id,
        premise=project.premise or "",
        genre=project.genre,
        style=project.style
    )
    
    # 生成角色卡
    characters = await planner.generate_character_cards(project_id, count=3)
    
    # 更新项目状态
    project.status = ProjectStatus.PLANNING
    await db.flush()
    
    return {
        "story_bible": story_bible,
        "characters": characters
    }


@router.post("/{project_id}/arcs/plan")
async def plan_arcs(
    project_id: int,
    total_arcs: int = 3,
    target_chapters_per_arc: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """规划卷/弧线"""
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    planner = PlannerService(db)
    arc_plan = await planner.generate_arc_plan(
        project_id=project_id,
        total_arcs=total_arcs,
        target_chapters_per_arc=target_chapters_per_arc
    )
    
    await db.flush()
    
    return arc_plan


@router.post("/{project_id}/chapters/plan")
async def plan_chapters(
    project_id: int,
    volume_id: int = None,
    chapter_count: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """规划章节大纲"""
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    planner = PlannerService(db)
    outlines = await planner.generate_chapter_outlines(
        project_id=project_id,
        volume_id=volume_id,
        count=chapter_count
    )
    
    await db.flush()
    
    return {"chapters": outlines}


@router.post("/{project_id}/outlines/{chapter_id}/revise")
async def revise_outline(
    project_id: int,
    chapter_id: int,
    revision_notes: str,
    db: AsyncSession = Depends(get_db)
):
    """修订章节大纲"""
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    planner = PlannerService(db)
    revised = await planner.revise_outline(chapter_id, revision_notes)
    
    await db.flush()
    
    return revised
