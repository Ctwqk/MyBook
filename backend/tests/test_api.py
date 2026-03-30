"""API 测试"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


class TestAPI:
    """API 测试类"""
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_create_project(self):
        """测试创建项目"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/projects",
                json={
                    "title": "测试小说",
                    "genre": "都市异能",
                    "premise": "测试 premise"
                }
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "测试小说"
        assert "id" in data
