# MyBook LLM Agent 配置指南

## 概览

MyBook 支持多种 LLM Provider，可以通过环境变量或 `.env` 文件进行配置。

## 配置方式

### 1. 创建 `.env` 文件

在项目根目录创建 `.env` 文件：

```bash
cp .env.example .env
```

### 2. 配置示例

#### 方案 A: OpenAI GPT-4

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=4096
```

#### 方案 B: Anthropic Claude

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_TEMPERATURE=0.7
ANTHROPIC_MAX_TOKENS=4096
```

#### 方案 C: Ollama 本地模型

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TEMPERATURE=0.7
OLLAMA_MAX_TOKENS=4096
```

#### 方案 D: SiliconFlow (国内 API)

```env
LLM_PROVIDER=siliconflow
SILICONFLOW_API_KEY=sk-xxxxx
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_MODEL=Qwen/Qwen2.5-7B-Instruct
SILICONFLOW_TEMPERATURE=0.7
SILICONFLOW_MAX_TOKENS=4096
```

#### 方案 E: DeepSeek

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TEMPERATURE=0.7
DEEPSEEK_MAX_TOKENS=4096
```

#### 方案 F: 智谱 AI (GLM)

```env
LLM_PROVIDER=zhipu
ZHIPU_API_KEY=xxxxx
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZHIPU_MODEL=glm-4
ZHIPU_TEMPERATURE=0.7
ZHIPU_MAX_TOKENS=4096
```

## 各模块独立配置

可以为不同的 Agent 模块指定不同的模型：

```env
# Planner 模块 - 负责规划、设定生成（通常需要更强的推理能力）
PLANNER_MODEL=gpt-4o

# Writer 模块 - 负责正文生成（需要创意和质量）
WRITER_MODEL=gpt-4o

# Reviewer 模块 - 负责审查（可以使用更小更快的模型）
REVIEWER_MODEL=gpt-4o-mini
```

## Provider 对比

| Provider | 优点 | 缺点 | 推荐场景 |
|----------|------|------|----------|
| OpenAI | 模型强大、稳定性好 | 需要翻墙、成本较高 | 追求质量 |
| Anthropic | Claude 3.5 能力强 | 需要翻墙、成本较高 | 长文本处理 |
| Ollama | 免费、本地运行 | 需要高性能机器 | 隐私敏感、调试 |
| SiliconFlow | 国内可用、便宜 | 模型相对较弱 | 国内用户、成本敏感 |
| DeepSeek | 性价比高 | 模型相对较新 | 成本敏感 |
| 智谱 GLM | 国内可用、中文优化 | 能力有限 | 国内用户 |
| Mock | 无需 API | 仅用于测试 | 开发调试 |

## 推荐的 Provider 组合

### 追求质量（需要翻墙）
```
PLANNER_MODEL=gpt-4o
WRITER_MODEL=gpt-4o
REVIEWER_MODEL=gpt-4o-mini
```

### 国内低成本
```
PLANNER_MODEL=deepseek-chat
WRITER_MODEL=deepseek-chat
REVIEWER_MODEL=Qwen/Qwen2.5-7B-Instruct
```

### 本地开发调试
```
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
```

## 代码中使用

### 直接创建 Provider

```python
from app.llm.factory import create_llm_provider

# 使用默认配置
provider = create_llm_provider()

# 指定 Provider
provider = create_llm_provider("openai", model="gpt-4o")

# 指定温度和 Token
provider = create_llm_provider("deepseek", temperature=0.8, max_tokens=8192)
```

### 为特定模块创建 Provider

```python
from app.llm.factory import create_module_provider

# 根据模块配置创建 Provider
planner_provider = create_module_provider("planner")
writer_provider = create_module_provider("writer")
reviewer_provider = create_module_provider("reviewer")
```

### 在 Service 中使用

```python
from app.llm.factory import create_module_provider

class MyService:
    async def do_something(self):
        provider = create_module_provider("writer")
        response = await provider.generate(
            "请生成一段小说开头",
            system_prompt="你是一个网络小说作家"
        )
        return response.content
```

## 环境变量优先级

1. 代码中直接传入的参数（如 `create_llm_provider(model="xxx")`）
2. `.env` 文件中的配置
3. `config.py` 中的默认值

## 故障排除

### Ollama 连接失败
```bash
# 确保 Ollama 服务正在运行
ollama serve

# 检查可用的模型
ollama list
```

### API Key 无效
- 检查 API Key 是否正确
- 检查是否有足够的配额
- 检查网络连接

### 超时错误
```python
# 在 Provider 初始化时增加超时
provider = OpenAIProvider(
    api_key="xxx",
    timeout=300.0  # 增加到 5 分钟
)
```
