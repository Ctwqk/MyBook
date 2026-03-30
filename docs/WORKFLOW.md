# MyBook 写作系统业务流程

## 一、核心链路

```
用户输入想法 → Planner 出蓝图 → Memory 组上下文 → Writer 写章节 → Reviewer 审查 → Memory 回写
```

### 审查失败分支

```
Reviewer 不通过 → 
  ├── patch_required: Writer 局部修补 → Reviewer 再审
  ├── rewrite_required + outline_ok: Writer 重写 → Reviewer 再审
  └── rewrite_required + outline_bad: Planner 修章纲 → Memory 重组 → Writer 重写 → Reviewer 再审
```

---

## 二、数据对象

### 1. StoryPackage (Planner 输出)
```python
{
    "structured_premise": {...},      # 结构化 premise
    "story_bible_draft": {...},        # Story Bible 初稿
    "character_cards": [...],          # 角色卡列表
    "arc_plans": [...],               # 卷纲列表
    "chapter_outlines": [...],         # 章纲列表
}
```

### 2. ContextPack (Memory 组装)
```python
{
    "chapter_outline": {...},          # 当前章纲
    "relevant_world_settings": [...],   # 相关世界观
    "relevant_character_states": [...], # 相关角色状态
    "recent_chapter_memories": [...],  # 近期章节摘要
    "current_arc_summary": "...",       # 当前卷摘要
    "active_foreshadows": [...],       # 活跃伏笔
    "review_warnings": [...],           # 审查警告
    "style_constraints": [...],         # 风格约束
    "word_count_target": 3000,
}
```

### 3. ChapterDraft (Writer 输出)
```python
{
    "chapter_text": "...",             # 正文
    "chapter_summary": "...",           # 摘要
    "character_state_changes": [...],    # 角色状态变化
    "new_world_details": [...],         # 新世界观细节
    "new_foreshadows": [...],           # 新伏笔
    "resolved_foreshadows": [...],      # 已解决伏笔
    "writer_notes": "...",              # 写作笔记
}
```

### 4. ReviewResult (Reviewer 输出)
```python
{
    "overall_verdict": "pass|patch_required|rewrite_required",
    "issue_list": [...],
    "rewrite_instructions": "...",
    "planner_feedback": "...",         # 章纲层面问题
    "memory_feedback": "...",           # 记忆一致性问题
    "consistency_score": 0.95,
    "pacing_score": 0.90,
    "hook_score": 0.85,
}
```

---

## 三、调用顺序

### A. 项目初始化

```
User → 创建项目 (Project)
    ↓
Planner.parse_premise() → StructuredPremise
    ↓
Planner.generate_story_bible() → StoryBible
    ↓
Planner.generate_character_cards() → Characters + CharacterStates
    ↓
Planner.generate_arc_plan() → ArcPlans
    ↓
Planner.generate_chapter_outlines() → ChapterOutlines
    ↓
Memory 持久化所有内容
```

### B. 单章生成

```
Orchestrator.run_generate_chapter()
    ↓
Memory.build_context_pack() → ContextPack
    ↓
Writer.generate_chapter() → ChapterDraft
    ↓
Orchestrator.run_review_loop()
    ↓
Reviewer.review_chapter() → ReviewResult
    ↓
[分支判断]
    ├── pass → Memory 回写
    ├── patch_required → Writer.patch_chapter() → 再审
    └── rewrite_required
            ├── outline_ok → Writer.rewrite_chapter() → 再审
            └── outline_bad → Planner.revise_outline() → Writer.generate_chapter() → 再审
```

---

## 四、Memory 回写规则

### 必须回写
1. **ChapterMemory** - 章节摘要、关键事件
2. **CharacterState** - 角色位置、目标、关系、情绪
3. **ArcMemory** - 当前卷推进进度
4. **ForeshadowRecord** - 新伏笔/已解决伏笔
5. **ReviewNote** - 审查问题记录

### 谨慎回写
- **StoryBible** - 仅当新设定满足：
  - 确实是长期稳定设定
  - Reviewer 未判定冲突
  - 不是临场口嗨

---

## 五、Orchestrator 接口

```python
from app.services.orchestrator import WritingOrchestrator

orchestrator = WritingOrchestrator()

# 项目引导
story_package = await orchestrator.run_bootstrap(
    project_id="xxx",
    premise="主角穿越到异世界...",
    genre="奇幻",
)

# 单章完整流程
draft, result = await orchestrator.run_full_chapter_workflow(
    project_id="xxx",
    chapter_id="ch_1",
)

# 分步执行
draft = await orchestrator.run_generate_chapter(project_id, chapter_id)
draft, result = await orchestrator.run_review_loop(project_id, chapter_id, draft)
await orchestrator.run_finalize_chapter(project_id, chapter_id, draft, result)

# 批量生成
results = await orchestrator.run_batch_chapters(
    project_id="xxx",
    chapter_ids=["ch_1", "ch_2", "ch_3"],
)
```

---

## 六、Reviewer 判定规则

| verdict | 条件 | 处理 |
|---------|------|------|
| pass | 无严重问题 | 直接回写 |
| patch_required | 局部问题 | Writer 修补 |
| rewrite_required | 大面积问题 | Writer 重写 |
| rewrite_required + planner_feedback | 章纲问题 | Planner 修订章纲 |

### 评分维度
- **consistency_score** (0-1): 设定/角色一致性
- **pacing_score** (0-1): 节奏控制
- **hook_score** (0-1): 章末钩子质量

---

## 七、最简 MVP 路径

```
1. Planner 生成前 10 章章纲
2. 选第 1 章
3. Memory 组上下文
4. Writer 生成正文
5. Reviewer 审查
6. Memory 回写
7. 进入第 2 章
```

这样可以快速验证核心闭环。
