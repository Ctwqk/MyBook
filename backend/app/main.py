"""FastAPI 应用入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import engine, Base
from app.api.routes import projects, chapters, memory, publish, platform, arc_envelopes, orchestrator, audience


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # 关闭时：清理资源
    await engine.dispose()


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="MyBook - 长篇网文生成系统",
        description="一个模块化的长篇网文写作系统工程",
        version="2.5.0",
        lifespan=lifespan
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(projects.router)
    app.include_router(chapters.router)
    app.include_router(memory.router)
    app.include_router(publish.router)
    app.include_router(platform.router)
    app.include_router(arc_envelopes.router)
    app.include_router(orchestrator.router)
    app.include_router(audience.router)
    
    # 健康检查
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "2.5.0"}
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8888, reload=True)
