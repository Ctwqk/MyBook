# MyBook 设计与代码差距分析文档

更新时间：2026-05-21

## 1. 分析概述

本文档对比了 ForWin 设计文档（Design-docs/）与当前 MyBook 代码的实际实现差距，并基于此规划实现方案。

### 1.1 设计文档来源

| 文档 | 状态 | 说明 |
|------|------|------|
| `CURRENT_ARCHITECTURE.md` | active-current | 当前架构入口 |
| `V4_final_book_state_runtime.md` | active-current | BookState 最终 runtime 规格 |
| `V4.5_markstone.md` | active-current | 代码与设计差距统一入口 |
| `V4.6_knowledge_system.md` | active-current | 三层知识系统 |
| `V4.7_character_personality_maintenance.md` | active-maintenance | 人物性格 runtime 维护 |
| `V4.8_character_creation_personality_assignment.md` | active-maintenance | 人物创建与性格分配 |
| `map_scheme_c.md` | active-current | Scheme C 地图最终语义 |

### 1.2 当前代码基线

- **版本**：v2.5.0
- **架构**：FastAPI 分层架构（API → Service → Repository → DB）
- **主要模块**：Orchestrator、Writer、Reviewer、Planner、Memory、Audience、Publish

---

## 2. 核心差距分析

### 2.1 BookState 世界状态系统

#### 设计要求

```
BookState = 
  ├── ObjectiveWorldGraph (世界节点/边/事实)
  ├── MapGraph (地图系统)
  ├── CognitionOverlay (认知层)
  ├── NarrativeControlGraph (叙事控制)
  └── DeltaLedger (增量账本)
```

#### 当前实现

| 组件 | 状态 | 说明 |
|------|------|------|
| `ObjectiveWorldGraph` | ❌ 未实现 | 无 `world_nodes`、`world_edges`、`fact_nodes` 表 |
| `MapGraph` | ⚠️ 部分实现 | 仅 `world_settings` 表，无分层地图结构 |
| `CognitionOverlay` | ❌ 未实现 | 无认知层概念 |
| `NarrativeControlGraph` | ⚠️ 部分实现 | `foreshadow_records` 仅作为伏笔记录 |
| `DeltaLedger` | ❌ 未实现 | 无 GraphDelta 追加账本 |

#### 差距详情

1. **世界节点模型**：当前只有简单 `Character`、`WorldSetting` 表，无 12 种节点类型
2. **地图系统**：无 `SubWorld → Region → MapNode → MapEdge` 分层结构
3. **状态变更**：当前是覆盖式更新，无 append-only delta ledger
4. **快照机制**：无 as-of chapter 查询、snapshot replay 能力

### 2.2 Canon 提交路径

#### 设计要求

```
WriterOutput
  → BookStateGraphDeltaExtractor
  → BookStateReviewGate
  → BookStateCompiler
  → GraphDelta append
  → Snapshot rebuild
```

#### 当前实现

```
WriterOutput.state_change_candidates
  → OrchestratorService.update_state()
  → MemoryService (覆盖式写入)
  → ReviewVerdict 记录
```

#### 差距详情

1. 无 GraphDeltaExtractor：LLM 输出不直接生成 patch
2. 无 BookStateReviewGate：无法做 deterministic patch 校验
3. 无 BookStateCompiler：不是 append-only ledger
4. 无 Snapshot 重建机制

### 2.3 三层知识系统

#### 设计要求

```
BookState DB Canon (唯一真相)
    ↓ export/projection
Obsidian Vault (人类可读)
    ↓ compile/role scope
Karpathy-style LLM KB (模型上下文)
```

#### 当前实现

- `MemoryService.build_context_pack()` 直接从 DB 组装上下文
- 无 Obsidian Vault 投影
- 无 LLM KB 文件系统
- 无 role-scoped context pack

### 2.4 人物性格系统

#### 设计要求

```
- personality_loadout (dominant/secondary/social_mask/stress_mode)
- PersonalityLoadoutAssigner (自动分配)
- CharacterCreationHelper (统一创建入口)
- Integrity Gate (严格性校验)
```

#### 当前实现

```python
class Character:
    personality: Mapped[Optional[str]] = mapped_column(Text)  # 简单文本
```

#### 差距详情

1. 无 `personality_loadout` 结构化 JSON
2. 无 `PersonalitySkillLibrary`
3. 无自动分配 policy 和 scoring
4. 无 `CharacterCreationHelper`
5. 无 Integrity Gate

### 2.5 地图系统 (Scheme C)

#### 设计要求

```
SubWorld → Region → MapNode → MapEdge
- SubWorld: continent/planet/plane/realm
- Region: kingdom/sect_domain/province
- MapNode: settlement/building/room/dungeon_room
- MapEdge: road/path/portal/hidden_route
- 路径算法: Dijkstra, metric 权重
```

#### 当前实现

```python
class WorldSetting:
    # 简单文本存储，无分层结构
    content: Mapped[str]
```

#### 差距详情

1. 无 `sub_worlds` 表
2. 无 `map_regions` 表
3. 无 `map_nodes` / `map_edges` 表
4. 无 `map_generation_runs`
5. 无路径计算算法
6. 无认知视角过滤

---

## 3. 非功能性差距

### 3.1 Observability

| 设计要求 | 当前实现 | 状态 |
|----------|----------|------|
| DecisionEvent 账本 | 无 | ❌ |
| PromptTrace | 无 | ❌ |
| ArtifactStore | ⚠️ `services/artifact/` 存在 | ⚠️ |
| Chapter Ledger | 无专门表 | ❌ |

### 3.2 Skill Runtime

| 设计要求 | 当前实现 | 状态 |
|----------|----------|------|
| Skill Library | 无 `forwin/skills/` | ❌ |
| Prompt Layer Integration | 硬编码 prompts | ⚠️ |
| PromptTrace 记录 | 无 | ❌ |

### 3.3 Arc/Band 体验计划

| 设计要求 | 当前实现 | 状态 |
|----------|----------|------|
| `ArcEnvelope` | ⚠️ 存在 | ⚠️ |
| `BandExperiencePlan` | ⚠️ 存在 | ⚠️ |
| Reader Experience Runtime | 无 | ❌ |
| Comment Signal Candidate | 无 | ❌ |

---

## 4. 实现规划

### Phase 1: BookState 基础层 (核心)

**目标**：建立最终世界状态的基础结构

| 任务 | 说明 | 优先级 |
|------|------|--------|
| 1.1 新增 `world_nodes` 表 | 12 种节点类型，profile_json + state_json | P0 |
| 1.2 新增 `world_edges` 表 | 50 种边类型，统一字段 | P0 |
| 1.3 新增 `fact_nodes` 表 | 结构化事实存储 | P1 |
| 1.4 新增 `graph_deltas` 表 | Append-only delta ledger | P0 |
| 1.5 实现 `GraphDeltaCompiler` | Patch apply + conflict 检测 | P0 |
| 1.6 实现 `WorldSnapshot` | As-of chapter 快照 | P1 |

**预计工作量**：中（2-3 周）

### Phase 2: 地图系统 (Scheme C)

**目标**：实现分层、带权、有向、多重图地图

| 任务 | 说明 | 优先级 |
|------|------|--------|
| 2.1 新增 `sub_worlds` 表扩展 | subworld_type/scale_level/generation_seed | P0 |
| 2.2 新增 `map_regions` 表 | region_role/culture_profile/danger_profile | P1 |
| 2.3 新增 `map_nodes` / `map_edges` 表 | 分层地点和路线 | P0 |
| 2.4 实现 `MapGenerator` | Graph-based weighted generation | P0 |
| 2.5 实现 Dijkstra 路径算法 | Metric 权重、hidden/blocked 过滤 | P0 |
| 2.6 实现认知视角路径 | `compute_known_distance()` | P1 |

**预计工作量**：中（2-3 周）

### Phase 3: Canon 提交路径

**目标**：重构 canon 提交为 BookState-first

| 任务 | 说明 | 优先级 |
|------|------|--------|
| 3.1 实现 `BookStateDeltaAdapter` | WriterOutput → GraphDeltaSet | P0 |
| 3.2 实现 `BookStateReviewGate` | Patch 校验 + 冲突检测 | P0 |
| 3.3 重构 `OrchestratorService` | BookState direct path | P0 |
| 3.4 实现 Snapshot 重建 | 接受章节后重建快照 | P1 |
| 3.5 迁移旧 Entity 投影 | entities → world_nodes | P2 |

**预计工作量**：大（3-4 周）

### Phase 4: 人物性格系统

**目标**：建立结构化性格 runtime

| 任务 | 说明 | 优先级 |
|------|------|--------|
| 4.1 扩展 `Character` 模型 | 添加 `personality_loadout` JSON | P0 |
| 4.2 实现 `PersonalityLoadoutAssigner` | 规则引擎 + scoring | P1 |
| 4.3 实现 `CharacterCreationHelper` | 统一创建入口 | P1 |
| 4.4 实现 Integrity Gate | 严格性校验 | P2 |
| 4.5 迁移旧 personality 文本 | 升级到结构化 | P2 |

**预计工作量**：中（2-3 周）

### Phase 5: 知识系统 (V4.6)

**目标**：实现三层知识投影

| 任务 | 说明 | 优先级 |
|------|------|--------|
| 5.1 实现 Obsidian Vault 导出 | Markdown + frontmatter | P2 |
| 5.2 实现 LLM KB 文件系统 | role-scoped context | P2 |
| 5.3 实现 Proposal/Approval 流程 | Obsidian 修改审核 | P2 |
| 5.4 实现 Vector Retrieval | embedding index | P3 |

**预计工作量**：大（4-5 周）

---

## 5. 实施建议

### 5.1 渐进式迁移

1. **保持兼容**：新旧系统双轨并存，逐步切换
2. **向后兼容**：旧 Entity 表保留为兼容投影
3. **Feature Flag**：使用配置开关控制新功能

### 5.2 优先级建议

**短期（1-2 月）**：
- Phase 1: BookState 基础层
- Phase 2: 地图系统

**中期（3-4 月）**：
- Phase 3: Canon 提交路径
- Phase 4: 人物性格系统

**长期（5+ 月）**：
- Phase 5: 知识系统

### 5.3 测试策略

```bash
# BookState 测试
pytest tests/test_book_state_*.py -q

# 地图测试  
pytest tests/test_map_*.py -q

# 集成测试
pytest tests/test_*_full.py -q
```

---

## 6. 附录

### A. 设计文档权威关系

```
CURRENT_ARCHITECTURE.md (入口)
    ├── V4_final_book_state_runtime.md (BookState 规格)
    │       └── V4.5_markstone.md (差距入口)
    ├── map_scheme_c.md (地图规格)
    ├── V4.6_knowledge_system.md (知识系统)
    ├── V4.7_character_personality_maintenance.md (性格维护)
    └── V4.8_character_creation_personality_assignment.md (人物创建)
```

### B. 关键不变量

1. BookState DB Canon 是唯一权威真相
2. 所有 canon 变更必须经过 ReviewGate
3. Delta ledger 是 append-only
4. SubWorld 只表示大尺度容器
5. 人物必须有有效 personality_loadout