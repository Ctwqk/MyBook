"""Performance runner smoke tests."""
from pathlib import Path

from httpx import ASGITransport, AsyncClient
import pytest

from app.api.deps import get_llm_provider
from app.db.session import get_db
from app.llm.mock import MockLLMProvider
from app.main import app
from app.services.performance.runner import PerformanceRunner
from app.services.performance.schemas import PerformanceRunRequest


class TestPerformanceRunner:
    @pytest.mark.asyncio
    async def test_run_mock_three_chapters_writes_report_artifacts(
        self,
        db_session,
        test_project,
        tmp_path: Path,
    ) -> None:
        runner = PerformanceRunner(
            db_session,
            llm_provider=MockLLMProvider(),
        )
        request = PerformanceRunRequest(
            chapter_count=3,
            target_word_count=2800,
            min_body_chars=2500,
            include_review=False,
            llm_provider="mock",
            report_root=str(tmp_path / "performance"),
            profile_cpu=True,
            profile_memory=True,
        )

        report = await runner.run(test_project.id, request)

        assert report.summary.total_chapters == 3
        assert report.summary.generated_chapters == 3
        assert report.summary.failed_chapters == 0
        assert report.summary.llm_call_count > 0
        assert report.summary.db_query_count > 0
        assert len(report.chapters) == 3
        assert all(chapter.status == "generated" for chapter in report.chapters)
        assert all(chapter.char_count >= 2500 for chapter in report.chapters)
        assert {metric.stage for metric in report.stage_metrics} >= {
            "planner.generate_chapter_outlines",
            "orchestrator.chapter_generation",
            "memory.build_context_pack",
            "writer.generate_single_pass",
        }

        run_dir = Path(report.summary.report_dir)
        assert (run_dir / "summary.md").exists()
        assert (run_dir / "stage_metrics.json").exists()
        assert (run_dir / "chapter_metrics.csv").exists()
        assert (run_dir / "cpu_top.txt").exists()
        assert (run_dir / "memory_top.txt").exists()
        assert (run_dir / "errors.md").exists()
        assert (run_dir / "optimization_plan.md").exists()
        assert (run_dir / "run_config.json").exists()
        assert (run_dir / "raw_profile.prof").exists()
        assert (run_dir / "tracemalloc_snapshot.txt").exists()

    @pytest.mark.asyncio
    async def test_performance_api_runs_mock_benchmark(
        self,
        db_session,
        test_project,
        tmp_path: Path,
    ) -> None:
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_llm_provider] = lambda: MockLLMProvider()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/projects/{test_project.id}/performance/run-30-chapters",
                    json={
                        "chapter_count": 2,
                        "target_word_count": 2800,
                        "min_body_chars": 2500,
                        "include_review": False,
                        "llm_provider": "mock",
                        "report_root": str(tmp_path / "api-performance"),
                    },
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"]["total_chapters"] == 2
        assert payload["summary"]["generated_chapters"] == 2
        assert payload["summary"]["completed"] is True
        assert Path(payload["summary"]["report_dir"], "summary.md").exists()
