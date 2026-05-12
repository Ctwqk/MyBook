"""Performance benchmark API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_llm_provider
from app.db.session import get_db
from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider
from app.services.performance.runner import PerformanceRunner
from app.services.performance.schemas import PerformanceRunReport, PerformanceRunRequest

router = APIRouter(prefix="/projects/{project_id}/performance", tags=["performance"])


@router.post("/run-30-chapters", response_model=PerformanceRunReport)
@router.post("/run-60-chapters", response_model=PerformanceRunReport)
async def run_chapter_performance(
    project_id: int,
    request: PerformanceRunRequest | None = None,
    db: AsyncSession = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
):
    """Run a sequential chapter-generation benchmark and write report artifacts."""
    request = request or PerformanceRunRequest()
    provider = MockLLMProvider() if request.llm_provider == "mock" else llm
    runner = PerformanceRunner(db, provider)
    try:
        return await runner.run(project_id, request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
