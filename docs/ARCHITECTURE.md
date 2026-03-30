# 系统架构文档

## 整体架构

MyBook 采用分层架构设计：

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                       │
├─────────────────────────────────────────────────────────────┤
│                       API Gateway                           │
├─────────────────────────────────────────────────────────────┤
│                      FastAPI Routes                         │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐        │
│  │Projects │ │ Chapters │ │ Memory  │ │ Publish │        │
│  └────┬────┘ └────┬─────┘ └────┬────┘ └────┬────┘        │
├───────┼───────────┼────────────┼───────────┼──────────────┤
│       │           │            │           │               │
│       ▼           ▼            ▼           ▼               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Service Layer                            │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐   │   │
│  │  │ Planner │ │ Writer  │ │Reviewer │ │ Publish  │   │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬───┘   │   │
│  │       │           │           │          │        │   │
│  │       └───────────┼───────────┼──────────┘        │   │
│  │                   │           │                   │   │
│  │                   ▼           ▼                   │   │
│  │              ┌──────────┐                           │   │
│  │              │  Memory  │◄────── LLM Provider       │   │
│  │              │ Service  │                           │   │
│  │              └────┬─────┘                           │   │
│  └───────────────────┼─────────────────────────────────┘   │
├──────────────────────┼──────────────────────────────────────┤
│                      ▼                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Repository Layer                         │   │
│  └──────────────────────┬───────────────────────────────┘   │
├───────────────────────┼────────────────────────────────────┤
│                       ▼                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Database (PostgreSQL)                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 模块职责

### API Layer
- 接收 HTTP 请求
- 参数验证
- 权限检查（预留）
- 路由分发

### Service Layer
- **PlannerService**: 负责故事规划，包括 premise 解析、Story Bible 生成、角色卡生成、卷纲章纲生成
- **WriterService**: 负责正文生成，包括章节生成、续写、重写、段落修补
- **ReviewerService**: 负责质量审查，包括一致性检查、节奏检查、钩子检查
- **MemoryService**: 负责状态管理和记忆，包括 Story Bible、角色状态、章节记忆、伏笔管理
- **PublishService**: 负责发布管理，包括平台会话、书籍绑定、任务状态机

### Repository Layer
- 数据库 CRUD 操作
- 查询优化

### LLM Provider Layer
- 统一的 LLM 调用接口
- 支持 Mock、OpenAI、Anthropic 等多 Provider

## 数据流

### 1. 创建项目并引导
```
用户 -> POST /projects -> 创建 Project
     -> POST /projects/{id}/bootstrap
        -> PlannerService.parse_premise()
        -> PlannerService.bootstrap_story() -> StoryBible
        -> PlannerService.generate_character_cards() -> Characters
```

### 2. 生成章节正文
```
用户 -> POST /projects/{id}/chapters/{cid}/generate
     -> WriterService.generate_chapter()
        -> MemoryService.build_context_pack() -> Context
        -> LLM.generate() -> Text
        -> WriterService._extract_chapter_data() -> Summary
        -> MemoryService.save_chapter_memory()
```

### 3. 审查章节
```
用户 -> POST /projects/{id}/chapters/{cid}/review
     -> ReviewerService.review_chapter()
        -> LLM.review()
        -> MemoryService.record_review_note()
```

## 状态机

### 项目状态
```
DRAFT -> PLANNING -> WRITING -> REVIEWING -> PUBLISHED
                                ↓
                            ARCHIVED
```

### 章节状态
```
OUTLINE -> DRAFT -> WRITING -> REVIEWING -> APPROVED -> PUBLISHED
```

### 发布任务状态
```
PENDING -> PREPARING -> SUBMITTING -> SUCCESS
              ↓            ↓
           CANCELLED    FAILED
```

## 扩展点

### 1. 多租户
- 在 Project 模型添加 tenant_id
- API 层添加租户过滤

### 2. 权限控制
- 添加 User/Role 模型
- API 层添加权限检查装饰器

### 3. 向量检索
- 集成 pgvector 或 Qdrant
- MemoryService.search_memory() 改为向量相似度搜索

### 4. 多模型调度
- 根据任务类型选择不同模型
- 实现模型路由逻辑

### 5. 异步任务
- 集成 Celery 或 FastAPI BackgroundTasks
- 长时间生成任务异步处理

### 6. 缓存
- 添加 Redis 缓存层
- 缓存 Story Bible、角色状态等热点数据
