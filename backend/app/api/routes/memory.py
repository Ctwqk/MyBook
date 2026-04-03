"""记忆相关 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.character import CharacterCreate, CharacterUpdate, CharacterResponse as CharacterResp
from app.schemas.memory import (
    StoryBibleResponse,
    StoryBibleUpdate,
    ContextPackRequest,
    ContextPackResponse,
    ForeshadowRecordCreate,
    ForeshadowRecordResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    ChapterMemoryCreate,
    ChapterMemoryResponse,
)
from app.services.memory.service import MemoryService

router = APIRouter(prefix="/projects/{project_id}/memory", tags=["memory"])


@router.get("/story-bible", response_model=StoryBibleResponse)
async def get_story_bible(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取 Story Bible - 如果不存在则自动创建空记录"""
    service = MemoryService(db)
    bible = await service.get_story_bible(project_id)
    
    # 如果不存在，自动创建空记录
    if not bible:
        bible = await service.update_story_bible(project_id, {
            "title": "",
            "genre": "",
            "theme": "",
            "synopsis": "",
            "tone": "",
            "target_audience": "",
        })
    
    return bible


@router.patch("/story-bible", response_model=StoryBibleResponse)
async def update_story_bible(
    project_id: int,
    updates: StoryBibleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新 Story Bible"""
    service = MemoryService(db)
    
    update_data = updates.model_dump(exclude_unset=True)
    bible = await service.update_story_bible(project_id, update_data)
    
    return bible


@router.get("/characters/state")
async def get_character_states(
    project_id: int,
    character_id: int = None,
    db: AsyncSession = Depends(get_db)
):
    """获取角色状态"""
    service = MemoryService(db)
    states = await service.get_character_states(project_id, character_id)
    
    return {"states": states}


@router.get("/characters", response_model=list[CharacterResp])
async def list_characters(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取项目角色列表"""
    service = MemoryService(db)
    characters = await service.get_characters(project_id)
    
    return characters


@router.post("/characters", response_model=CharacterResp, status_code=status.HTTP_201_CREATED)
async def create_character(
    project_id: int,
    character_data: CharacterCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建新角色"""
    service = MemoryService(db)
    
    data = character_data.model_dump(exclude_unset=True)
    data["project_id"] = project_id
    
    character = await service.create_character(
        project_id=project_id,
        data=data
    )
    
    return character


@router.post("/characters/state")
async def update_character_state(
    project_id: int,
    character_id: int,
    state_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """更新角色状态"""
    service = MemoryService(db)
    state = await service.update_character_states(project_id, character_id, state_data)
    
    return state


@router.get("/search", response_model=MemorySearchResponse)
async def search_memory(
    project_id: int,
    query: str,
    search_type: str = "all",
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """搜索记忆"""
    service = MemoryService(db)
    results = await service.search_memory(project_id, query, search_type)
    
    return MemorySearchResponse(results=results[:limit], total=len(results))


@router.post("/context-pack", response_model=ContextPackResponse)
async def build_context_pack(
    project_id: int,
    request: ContextPackRequest,
    db: AsyncSession = Depends(get_db)
):
    """构建上下文包"""
    try:
        service = MemoryService(db)
        context = await service.build_context_pack(project_id, request)
        
        # 确保所有字段都是可序列化的
        return {
            "story_bible": context.story_bible,
            "character_states": context.character_states or [],
            "recent_chapters": context.recent_chapters or [],
            "foreshadows": context.foreshadows or [],
            "pending_reviews": context.pending_reviews or [],
            "formatted_context": context.formatted_context or ""
        }
    except Exception as e:
        # 记录错误并返回空上下文
        import logging
        logging.getLogger(__name__).error(f"构建上下文包失败: {e}")
        return {
            "story_bible": None,
            "character_states": [],
            "recent_chapters": [],
            "foreshadows": [],
            "pending_reviews": [],
            "formatted_context": "上下文构建失败，请稍后重试"
        }


@router.post("/chapter", response_model=ChapterMemoryResponse)
async def save_chapter_memory(
    project_id: int,
    request: ChapterMemoryCreate,
    db: AsyncSession = Depends(get_db)
):
    """保存章节记忆"""
    service = MemoryService(db)
    
    memory_data = request.model_dump(exclude_unset=True)
    memory = await service.save_chapter_memory(
        project_id=request.chapter_id,
        chapter_id=request.chapter_id,
        memory_data=memory_data
    )
    
    return memory


@router.get("/foreshadow")
async def get_foreshadows(
    project_id: int,
    include_resolved: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """获取伏笔列表"""
    service = MemoryService(db)
    
    if include_resolved:
        # TODO: 获取所有伏笔
        foreshadows = []
    else:
        foreshadows = await service.get_active_foreshadows(project_id)
    
    # 转换为可序列化格式
    result = []
    for f in foreshadows:
        result.append({
            "id": f.id,
            "project_id": f.project_id,
            "chapter_id": f.chapter_id,
            "content": f.content,
            "related_entities": f.related_entities,
            "status": f.status.value if hasattr(f.status, 'value') else str(f.status),
            "planned_resolution": f.planned_resolution,
            "created_at": f.created_at,
            "updated_at": f.updated_at
        })
    
    return result


@router.post("/foreshadow", response_model=ForeshadowRecordResponse)
async def record_foreshadow(
    project_id: int,
    request: ForeshadowRecordCreate,
    db: AsyncSession = Depends(get_db)
):
    """记录伏笔"""
    service = MemoryService(db)
    
    foreshadow = await service.record_foreshadow(
        project_id=project_id,
        chapter_id=request.chapter_id,
        content=request.content,
        related_entities=request.related_entities,
        planned_resolution=request.planned_resolution
    )
    
    return foreshadow


@router.patch("/foreshadow/{foreshadow_id}/resolve", response_model=ForeshadowRecordResponse)
async def resolve_foreshadow(
    project_id: int,
    foreshadow_id: int,
    db: AsyncSession = Depends(get_db)
):
    """解决伏笔"""
    service = MemoryService(db)
    foreshadow = await service.resolve_foreshadow(foreshadow_id)
    
    return foreshadow


@router.post("/review-note")
async def record_review_note(
    project_id: int,
    chapter_id: int,
    issue_type: str,
    severity: str,
    description: str,
    fix_suggestion: str = None,
    db: AsyncSession = Depends(get_db)
):
    """记录审查笔记"""
    service = MemoryService(db)
    
    note = await service.record_review_note(
        project_id=project_id,
        chapter_id=chapter_id,
        issue_type=issue_type,
        severity=severity,
        description=description,
        fix_suggestion=fix_suggestion
    )
    
    return note


@router.get("/review-notes")
async def get_review_notes(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取审查笔记"""
    service = MemoryService(db)
    notes = await service.get_pending_reviews(project_id)
    
    return {"notes": notes}
