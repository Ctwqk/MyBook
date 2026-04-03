"""章节相关 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.chapter import Chapter, ChapterStatus
from app.repositories.chapter import ChapterRepository
from app.schemas.chapter import (
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    GenerateChapterRequest,
    ContinueChapterRequest,
    RewriteChapterRequest,
    PatchChapterRequest,
)
from app.schemas.review import (
    ReviewRequest,
    ReviewResponse,
    PartialReviewRequest,
    RewriteInstructionsResponse,
)
from app.services.writer.service import WriterService
from app.services.reviewer.service import ReviewerService
from app.api.deps import get_writer_service, get_reviewer_service

router = APIRouter(prefix="/projects/{project_id}/chapters", tags=["chapters"])


def get_chapter_or_404(repo: ChapterRepository, chapter_id: int, project_id: int) -> Chapter:
    """获取章节或抛出 404"""
    chapter = repo.chapter_repo.get(chapter_id) if hasattr(repo, 'chapter_repo') else None
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_id} not found"
        )
    return chapter


@router.post("", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED)
async def create_chapter(
    project_id: int,
    data: ChapterCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建新章节"""
    repo = ChapterRepository(db)
    
    # 获取下一个章节号
    next_no = await repo.get_next_chapter_no(project_id)
    
    chapter = Chapter(
        project_id=project_id,
        volume_id=data.volume_id,
        chapter_no=data.chapter_no or next_no,
        title=data.title,
        outline=data.outline,
        hook=data.hook,
        status=ChapterStatus.OUTLINE
    )
    
    db.add(chapter)
    await db.flush()
    await db.refresh(chapter)
    
    return chapter


@router.get("", response_model=list[ChapterResponse])
async def list_chapters(
    project_id: int,
    volume_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取章节列表"""
    repo = ChapterRepository(db)
    
    if volume_id:
        chapters = await repo.get_by_volume(volume_id)
    else:
        chapters = await repo.get_by_project(project_id, skip, limit)
    
    return chapters


@router.get("/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(
    project_id: int,
    chapter_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取章节详情"""
    repo = ChapterRepository(db)
    chapter = await repo.get(chapter_id)
    
    if not chapter or chapter.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_id} not found"
        )
    
    return chapter


@router.patch("/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    project_id: int,
    chapter_id: int,
    data: ChapterUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新章节"""
    repo = ChapterRepository(db)
    chapter = await repo.get(chapter_id)
    
    if not chapter or chapter.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_id} not found"
        )
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(chapter, key, value)
    
    await db.flush()
    await db.refresh(chapter)
    
    return chapter


# ==================== 写作相关 API ====================

@router.post("/{chapter_id}/generate")
async def generate_chapter_text(
    project_id: int,
    chapter_id: int,
    request: GenerateChapterRequest = None,
    db: AsyncSession = Depends(get_db),
    writer: WriterService = Depends(get_writer_service)
):
    """生成章节正文"""
    repo = ChapterRepository(db)
    chapter = await repo.get(chapter_id)
    
    if not chapter or chapter.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_id} not found"
        )
    
    if request is None:
        request = GenerateChapterRequest()
    
    result = await writer.generate_chapter(project_id, chapter_id, request)
    
    # WriterOutput 是 Pydantic 模型，提取属性
    draft_blob = result.draft_blob if hasattr(result, 'draft_blob') else str(result)
    word_count = len(draft_blob) // 2
    
    return {
        "chapter_id": chapter_id,
        "text": draft_blob,
        "word_count": word_count,
        "summary": result.chapter_summary if hasattr(result, 'chapter_summary') else None
    }


@router.post("/{chapter_id}/continue")
async def continue_chapter_text(
    project_id: int,
    chapter_id: int,
    request: ContinueChapterRequest,
    db: AsyncSession = Depends(get_db)
):
    """续写章节"""
    repo = ChapterRepository(db)
    chapter = await repo.get(chapter_id)
    
    if not chapter or chapter.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_id} not found"
        )
    
    writer = WriterService(db)
    result = await writer.continue_chapter(project_id, chapter_id, request)
    
    return {
        "chapter_id": chapter_id,
        "continuation": result["continuation"],
        "new_word_count": result["new_word_count"]
    }


@router.post("/{chapter_id}/rewrite")
async def rewrite_chapter_text(
    project_id: int,
    chapter_id: int,
    request: RewriteChapterRequest,
    db: AsyncSession = Depends(get_db)
):
    """重写章节"""
    repo = ChapterRepository(db)
    chapter = await repo.get(chapter_id)
    
    if not chapter or chapter.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_id} not found"
        )
    
    writer = WriterService(db)
    result = await writer.rewrite_chapter(project_id, chapter_id, request)
    
    return {
        "chapter_id": chapter_id,
        "rewritten_text": result["rewritten_text"],
        "word_count": result["word_count"]
    }


@router.post("/{chapter_id}/patch")
async def patch_chapter_segment(
    project_id: int,
    chapter_id: int,
    request: PatchChapterRequest,
    db: AsyncSession = Depends(get_db)
):
    """修补章节段落"""
    repo = ChapterRepository(db)
    chapter = await repo.get(chapter_id)
    
    if not chapter or chapter.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_id} not found"
        )
    
    writer = WriterService(db)
    result = await writer.patch_chapter_segment(project_id, chapter_id, request)
    
    return {
        "chapter_id": chapter_id,
        "patched_segment": result["patched_segment"],
        "new_word_count": result["new_word_count"]
    }


# ==================== 审查相关 API ====================

@router.post("/{chapter_id}/review")
async def review_chapter(
    project_id: int,
    chapter_id: int,
    request: ReviewRequest = None,
    db: AsyncSession = Depends(get_db),
    reviewer: ReviewerService = Depends(get_reviewer_service)
):
    """审查章节"""
    repo = ChapterRepository(db)
    chapter = await repo.get(chapter_id)
    
    if not chapter or chapter.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_id} not found"
        )
    
    if request is None:
        request = ReviewRequest()
    
    result = await reviewer.review_chapter(project_id, chapter_id, request)

    # 转换issues为可序列化格式（避免枚举类型序列化问题）
    issues = []
    for issue in result.issues:
        if hasattr(issue, 'model_dump'):
            issues.append(issue.model_dump())
        elif isinstance(issue, dict):
            issues.append(issue)
        else:
            issues.append({"description": str(issue)})

    return {
        "chapter_id": chapter_id,
        "verdict": result.verdict,
        "verdict_reason": result.verdict_reason,
        "issues": issues,
        "scores": result.scores if isinstance(result.scores, dict) else {},
        "review_notes": []
    }


@router.post("/{chapter_id}/review/partial", response_model=ReviewResponse)
async def partial_review_chapter(
    project_id: int,
    chapter_id: int,
    request: PartialReviewRequest,
    db: AsyncSession = Depends(get_db)
):
    """部分审查章节"""
    repo = ChapterRepository(db)
    chapter = await repo.get(chapter_id)
    
    if not chapter or chapter.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_id} not found"
        )
    
    reviewer = ReviewerService(db)
    result = await reviewer.review_partial(project_id, chapter_id, request)
    
    return result


@router.post("/{chapter_id}/rewrite-instructions", response_model=RewriteInstructionsResponse)
async def get_rewrite_instructions(
    project_id: int,
    chapter_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取重写指令"""
    repo = ChapterRepository(db)
    chapter = await repo.get(chapter_id)
    
    if not chapter or chapter.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_id} not found"
        )
    
    reviewer = ReviewerService(db)
    result = await reviewer.build_rewrite_instructions(project_id, chapter_id)
    
    return result
