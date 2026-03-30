# MyBook - 长篇网文生成系统

一个模块化的长篇网文写作系统工程，支持从 premise 到完整章节生成的完整流程。

## 特性

- 🎯 **模块化设计**: Planner / Memory / Writer / Reviewer / Publish 五大核心模块
- 🔌 **LLM Provider 抽象**: 支持 Mock/OpenAI/Anthropic 等多种 Provider
- 🐳 **Docker 容器化**: 一键部署
- 🧪 **全面测试**: 14 个测试文件，覆盖所有核心功能
- 📊 **完整数据模型**: 11 个核心实体，结构化存储

## 快速开始

### Docker 部署 (推荐)

```bash
# 启动所有服务
docker-compose up -d

# 服务地址:
# - Frontend: http://localhost:3000
# - Backend: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### 本地开发

```bash
# 安装后端依赖
cd backend
pip install -e .

# 安装前端依赖
cd ../frontend
npm install

# 启动后端
cd backend
uvicorn app.main:app --reload --port 8000

# 启动前端 (新终端)
cd frontend
npm run dev
```

## 项目结构

```
MyBook/
├── backend/                 # Python/FastAPI 后端
│   ├── app/
│   │   ├── api/routes/     # API 路由
│   │   ├── core/          # 核心配置
│   │   ├── db/            # 数据库会话
│   │   ├── llm/           # LLM Provider 抽象
│   │   ├── models/         # SQLAlchemy 模型
│   │   ├── repositories/   # 数据仓储
│   │   ├── schemas/        # Pydantic schemas
│   │   └── services/      # 业务服务
│   │       ├── planner/    # 规划服务
│   │       ├── memory/     # 记忆服务
│   │       ├── writer/     # 写作服务
│   │       ├── reviewer/   # 审查服务
│   │       └── publish/    # 发布服务
│   └── tests/              # 测试 (14 个文件)
├── frontend/               # React/TypeScript 前端
│   └── src/
│       ├── api/           # API 调用
│       ├── components/    # 组件
│       ├── pages/         # 页面
│       └── store/         # 状态管理
├── docs/                  # 文档
├── docker-compose.yml     # Docker 配置
└── Makefile              # 构建命令
```

## 核心模块

### 1. Planner (规划服务)
- `parse_premise`: 解析 premise
- `bootstrap_story`: 生成 Story Bible
- `generate_character_cards`: 生成角色卡
- `generate_arc_plan`: 生成卷纲
- `generate_chapter_outlines`: 生成章纲
- `revise_outline`: 修订大纲

### 2. Memory (记忆服务)
- Story Bible / 角色状态 / 章节记忆
- 伏笔管理 (record_foreshadow, resolve_foreshadow)
- 上下文包构建 (build_context_pack)
- 记忆搜索 (search_memory)

### 3. Writer (写作服务)
- `generate_chapter`: 生成正文
- `continue_chapter`: 续写
- `rewrite_chapter`: 重写
- `patch_chapter_segment`: 修补段落

### 4. Reviewer (审查服务)
- `review_chapter`: 完整审查
- `review_partial`: 部分审查
- `build_rewrite_instructions`: 生成重写指令

### 5. Publish (发布服务)
- 平台适配器接口
- 发布任务状态机
- Mock Adapter (dry-run)

## API 文档

启动后访问: http://localhost:8000/docs

### 主要端点

| 端点 | 描述 |
|------|------|
| `POST /projects` | 创建项目 |
| `POST /projects/{id}/bootstrap` | 引导项目 |
| `POST /projects/{id}/chapters/{cid}/generate` | 生成章节 |
| `POST /projects/{id}/chapters/{cid}/review` | 审查章节 |
| `POST /projects/{id}/publish/submit` | 发布章节 |

## 测试

```bash
# 运行所有测试
make test

# 运行测试并生成覆盖率
make test-coverage

# 直接运行 pytest
pytest -v
```

### 测试覆盖

- `test_models.py` - 模型和 Schema 测试
- `test_planner.py` / `test_planner_full.py` - Planner 测试
- `test_memory.py` / `test_memory_full.py` - Memory 测试
- `test_writer.py` / `test_writer_full.py` - Writer 测试
- `test_reviewer.py` / `test_reviewer_full.py` - Reviewer 测试
- `test_publish.py` / `test_publish_full.py` - Publish 测试
- `test_llm.py` / `test_llm_full.py` - LLM Provider 测试
- `test_api.py` - API 测试

## 数据模型 (11 个核心实体)

- **Project** - 项目
- **Character** - 角色
- **CharacterState** - 角色状态
- **WorldSetting** - 世界设定
- **Volume** - 卷/弧线
- **Chapter** - 章节
- **ChapterMemory** - 章节记忆
- **StoryBible** - 故事圣经
- **ForeshadowRecord** - 伏笔记录
- **ReviewNote** - 审查笔记
- **PublishTask** - 发布任务

## Docker

### 生产环境
```bash
docker-compose up -d
```

### 开发环境
```bash
docker-compose -f docker-compose.dev.yml up
```

### 单独构建
```bash
# 构建后端
docker build -f backend/Dockerfile -t mybook-backend .

# 构建前端
docker build -f frontend/Dockerfile -t mybook-frontend .
```

## 扩展点

- **LLM Provider**: 实现 `app/llm/base.py` 中的 `LLMProvider` 接口
- **发布平台**: 实现 `app/services/publish/adapter.py` 中的 `PlatformAdapter` 接口
- **向量检索**: 集成 pgvector 或 Qdrant
- **多租户**: 添加 tenant_id 字段

## 技术栈

- **后端**: Python 3.11, FastAPI, SQLAlchemy, Pydantic, PostgreSQL
- **前端**: React 18, TypeScript, Ant Design, Zustand
- **容器**: Docker, Docker Compose
- **测试**: pytest, pytest-asyncio

## License

MIT
