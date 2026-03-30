# 后端特定说明

## 依赖安装

```bash
# 使用 uv (推荐)
uv pip install -e .

# 或使用 pip
pip install -e .
```

## 环境变量

```bash
cp .env.example .env
```

主要配置项:
- `DATABASE_URL`: PostgreSQL 连接字符串
- `LLM_PROVIDER`: LLM 提供商 (mock/openai/anthropic)
- `OPENAI_API_KEY`: OpenAI API Key
- `ANTHROPIC_API_KEY`: Anthropic API Key

## 数据库

### 初始化
```bash
python run.py
```

### 使用 Alembic (推荐用于生产)
```bash
alembic init alembic
alembic revision --autogenerate -m "Initial"
alembic upgrade head
```

## 运行

```bash
# 开发模式
uvicorn app.main:app --reload --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 测试

```bash
# 运行所有测试
pytest

# 带覆盖率
pytest --cov=app --cov-report=html

# 特定文件
pytest tests/test_planner.py -v

# Watch 模式
ptw  # pip install pytest-watch
```

## LLM Provider

### Mock (默认)
用于开发测试，返回预设的模拟响应。

### OpenAI
```python
# 实现 OpenAIProvider 并在 factory.py 注册
```

### Anthropic
```python
# 实现 AnthropicProvider 并在 factory.py 注册
```

## 目录结构说明

```
backend/
├── app/
│   ├── api/          # API 层
│   │   ├── routes/  # 路由定义
│   │   ├── deps.py  # 依赖注入
│   │   └── main.py  # 应用入口
│   ├── core/         # 核心配置
│   │   ├── config.py
│   │   └── exceptions.py
│   ├── db/           # 数据库
│   │   └── session.py
│   ├── llm/          # LLM 抽象
│   │   ├── base.py
│   │   ├── mock.py
│   │   └── factory.py
│   ├── models/       # ORM 模型
│   ├── repositories/ # 数据仓储
│   ├── schemas/      # Pydantic 模型
│   └── services/     # 业务逻辑
│       ├── planner/
│       ├── memory/
│       ├── writer/
│       ├── reviewer/
│       └── publish/
└── tests/            # 测试
```
