# API 文档

## 项目接口

### 创建项目
```
POST /projects
```

**请求体:**
```json
{
  "title": "我的小说",
  "genre": "都市异能",
  "style": "热血",
  "premise": "一个普通大学生获得超能力的故事",
  "target_length": 500000
}
```

**响应:**
```json
{
  "id": 1,
  "title": "我的小说",
  "genre": "都市异能",
  "style": "热血",
  "premise": "...",
  "status": "draft",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### 获取项目列表
```
GET /projects
```

**查询参数:**
- `skip`: 跳过数量 (默认 0)
- `limit`: 限制数量 (默认 20)
- `status`: 按状态筛选

### 引导项目
```
POST /projects/{id}/bootstrap
```

自动执行:
1. 解析 premise
2. 生成 Story Bible
3. 生成主要角色卡

### 规划弧线
```
POST /projects/{id}/arcs/plan
```

**参数:**
- `total_arcs`: 总弧线数 (默认 3)
- `target_chapters_per_arc`: 每弧线章节数 (默认 30)

### 规划章节
```
POST /projects/{id}/chapters/plan
```

**参数:**
- `volume_id`: 卷 ID (可选)
- `chapter_count`: 章节数量 (默认 10)

## 章节接口

### 创建章节
```
POST /projects/{id}/chapters
```

### 生成正文
```
POST /projects/{id}/chapters/{chapter_id}/generate
```

**请求体:**
```json
{
  "outline": "自定义大纲 (可选)",
  "style_hints": "风格提示 (可选)"
}
```

### 续写章节
```
POST /projects/{id}/chapters/{chapter_id}/continue
```

**请求体:**
```json
{
  "last_paragraph": "最后一段内容 (可选)",
  "target_word_count": 3000
}
```

### 重写章节
```
POST /projects/{id}/chapters/{chapter_id}/rewrite
```

**请求体:**
```json
{
  "rewrite_instructions": "重写指令: 改善对话自然度"
}
```

### 审查章节
```
POST /projects/{id}/chapters/{chapter_id}/review
```

**请求体:**
```json
{
  "check_types": ["consistency", "pacing", "hook"]
}
```

**响应:**
```json
{
  "chapter_id": 1,
  "verdict": {
    "approved": true,
    "score": 7.5,
    "issues": [
      {
        "issue_type": "pacing",
        "severity": "low",
        "description": "第3段节奏稍慢",
        "fix_suggestion": "精简描写"
      }
    ],
    "summary": "章节整体质量良好"
  }
}
```

## 记忆接口

### 获取 Story Bible
```
GET /projects/{id}/memory/story-bible
```

### 构建上下文包
```
POST /projects/{id}/memory/context-pack
```

**请求体:**
```json
{
  "chapter_id": 1,
  "include_story_bible": true,
  "include_character_states": true,
  "include_recent_chapters": 3,
  "include_foreshadows": true
}
```

### 记录伏笔
```
POST /projects/{id}/memory/foreshadow
```

**请求体:**
```json
{
  "chapter_id": 1,
  "content": "古籍上的神秘符号",
  "related_entities": ["古籍", "符号"],
  "planned_resolution": "在第10章解开"
}
```

### 搜索记忆
```
GET /projects/{id}/memory/search
```

**参数:**
- `query`: 搜索关键词
- `search_type`: all, character, world, plot
- `limit`: 结果数量

## 发布接口

### 注册平台会话
```
POST /platform/accounts/register-session
```

**请求体:**
```json
{
  "platform": "mock",
  "session_token": "your_session_token"
}
```

### 发布章节
```
POST /projects/{id}/publish/submit
```

**请求体:**
```json
{
  "chapter_id": 1,
  "platform": "mock",
  "account_id": "account_123",
  "remote_book_id": "book_456",
  "mode": "immediate"
}
```

### 获取发布任务
```
GET /projects/{id}/publish/tasks
```

### 同步任务状态
```
POST /projects/{id}/publish/tasks/{task_id}/sync
```

## 错误码

### 发布错误码
- `SESSION_EXPIRED`: 会话过期
- `BOOK_NOT_BOUND`: 书籍未绑定
- `NETWORK_ERROR`: 网络错误
- `PLATFORM_VALIDATION_ERROR`: 平台验证错误
- `DUPLICATE_SUBMISSION`: 重复提交
- `PLATFORM_LAYOUT_CHANGED`: 平台页面变更
- `CONTENT_FORMAT_ERROR`: 内容格式错误
- `RISK_CONTROL_BLOCKED`: 风控拦截
