# Arc 规划系统 v2.4（修订版）：百分比 + 上下限 + 总长度分档 + Provisional 预演

## 0. 核心决定

这一版正式采用下面这套组合：

> **先用"百分比 + 上下限"给出 arc 的基础 target，  
> 再根据全书总长度分档决定这个 target 和 range 应该有多宽，  
> 然后每个 arc 在真正进入正文前，先走一轮 provisional 预演，  
> 再确定该 arc 的最终 envelope 与近端计划。**

也就是说，v2.4 不是：
- 一开始把所有 arc 的长度写死
- 也不是只靠 runtime 临场漂移

而是：
1. **有基础公式**
2. **有按总长度分档的浮动**
3. **有每个 arc 的 provisional 预演**
4. **最后才确定该 arc 的执行包络**

---

## 1. 三层决定机制

每个 arc 的结构，不再由单一规则决定，而是分三层：

### Layer 1：基础 target 计算
这是"百分比 + 上下限"。
- 给 arc 一个初始 target
- 防止系统一开始完全没边界

### Layer 2：按全书总长度分档调整
同样是一个 18 章 target：
- 对 100 章小说，它已经是一个比较大的段
- 对 1000 章小说，它可能只是一个过渡段

所以 range 的宽窄不能一样。

### Layer 3：每个 arc 单独做 provisional 预演
即使 total=100、target=18，也不能直接拿这个 target 当定案。  
系统要先对当前 arc 做一轮 provisional 预演，再决定：
- 这个 arc 是不是该扩
- 是不是该缩
- 当前 arc 的 detailed band 应该多长
- 当前 arc 的 frozen zone 应该多长

---

## 2. Layer 1：基础 target 规则（百分比 + 上下限）

### 2.1 基础目标
每个 active arc 都先算一个：
```text
base_target_size = clamp(round(total_chapters * ratio), min_size, max_size)
```

### 2.2 为什么必须同时有百分比和上下限

| 方案 | 问题 |
|------|------|
| 只用固定章节数 | 100章可能还行，1000章显得太碎 |
| 只用百分比 | 小项目会抖得很厉害，用户和产品不直观 |

**最佳做法**：同时有百分比 + 上下限
- 用百分比决定趋势
- 用上下限防止极端失真
- 最后落成整数章节数执行

---

## 3. Layer 2：按全书总长度分档

### 3.1 短长篇（1 ~ 150 章）

```text
arc_target = clamp(round(total_chapters * 0.18), 12, 24)
soft_min = target * 0.75
soft_max = target * 1.25
```

### 3.2 中长篇（151 ~ 400 章）

```text
arc_target = clamp(round(total_chapters * 0.15), 16, 30)
soft_min = target * 0.65
soft_max = target * 1.50
```

### 3.3 长连载（401 ~ 800 章）

```text
arc_target = clamp(round(total_chapters * 0.10), 20, 40)
soft_min = target * 0.55
soft_max = target * 1.70
```

### 3.4 超长连载（801+ 章）

```text
arc_target = clamp(round(total_chapters * 0.08), 24, 48)
soft_min = target * 0.50
soft_max = target * 2.00
```

### 3.5 这一层决定什么

这一层决定的是：
- 当前 arc 的 **先验 target**
- 当前 arc 的 **基础 soft range**

它还没有决定：
- 当前 arc 真实该结束在第几章
- detailed band 具体该多长
- frozen zone 应该多长

这些都留给 Layer 3。

---

## 4. Layer 3：Provisional 预演

每个 active arc 真正开写前，都先走一轮：

### 4.1 Provisional Arc Simulation 流程

#### Step 1：激活当前 arc
根据 total_chapters、当前分档、百分比+上下限公式算出：
- `base_target_size`
- `base_soft_min`
- `base_soft_max`

#### Step 2：生成 ArcStructureDraft
Arc Director 做中层结构规划，回答：
- 当前 arc 的主要矛盾是什么
- 哪些角色要活跃
- 哪些 thread 要推进 / 回收
- 高潮大概应该落在哪里
- 当前 arc 的功能是什么

输出 `ArcStructureDraft`：
- phase_layout
- key_beats
- thread_priorities
- hotspot_candidates
- compression_candidates

#### Step 3：生成 provisional band
在当前 arc 内生成一个近端的 provisional detailed band（例如前 5~8 章）

#### Step 4：Shadow 分支预演
按 Writer 逻辑真正写一点内容：
- scene breakdown
- scene generation
- stitch / polish
- structured extraction
- Continuity Review

进入：
- provisional chapter drafts
- provisional events
- provisional states
- provisional thread beats
- provisional timeline

#### Step 5：Arc Envelope Analysis
读取所有 provisional 数据，判断：

| 结果 | 说明 |
|------|------|
| **Keep** | 结构和正文预演一致，当前 target 合理 |
| **Expand** | 热点后移、核心冲突仍在升温、高潮还没到、高价值角色/thread 更有生命力 |
| **Compress** | 主问题已解、章节功能重复、中段偏水、继续按原 target 只会拖 |

#### Step 6：确定 resolved envelope
最终确定：
- `resolved_target_size`
- `resolved_soft_min`
- `resolved_soft_max`
- `resolved_detailed_band_size`
- `resolved_frozen_zone_size`

---

## 5. 近端 band 和 frozen zone 规则

### 5.1 Detailed Band
```text
detailed_band = clamp(round(resolved_target_size * 0.40), 4, 12)
```

### 5.2 Frozen Zone
```text
frozen_zone = clamp(round(detailed_band * 0.35), 2, 4)
```

**原则**：不要冻结太多章，否则动态性会迅速下降。frozen zone 只是"近期不轻易改"，不是永远不动。

---

## 6. 正文执行流程（正式线）

1. Writer 按章或按 scene 正式生成正文
2. Reviewer 审查
3. State Updater 先写 provisional，再 promote
4. 当一个小 band 稳定后 promote 到 canonical

---

## 7. Expansion / Compression 信号

### Expansion Signals（满足越多越倾向扩）
1. 主高潮尚未到来
2. 关键 thread 仍在升温
3. 最近 2~3 章冲突递增，不重复
4. 高价值角色活跃度上升
5. 时间推进合理
6. hook 强且指向 arc 主问题

### Compression Signals（满足越多越倾向缩）
1. 主问题已解
2. 最近章节功能重复
3. 没有新冲突，只是在搬运信息
4. 高潮已过，只剩拖尾
5. 时间推进过载
6. Pacing 分析判定"水"

---

## 8. 与 v2.3 的兼容性

### 保留 v2.3 的：
- 弱规划
- 分 scene Writer
- patch / reband / rearc
- cooldown
- 黑箱 / 检查点 / 共驾模式
- 结构化状态账本
- 时间系统
- Retrieval Broker

### 新增 v2.4 的：
- Arc target 分档规则
- Arc range 分档规则
- 每个 arc 的 provisional 预演
- Arc envelope analysis
- resolved envelope

---

## 9. 数据模型

### ArcEnvelope
```python
class ArcEnvelope:
    arc_id: int
    base_target_size: int          # 公式计算的基础值
    base_soft_min: int             # 基础下限
    base_soft_max: int             # 基础上限
    resolved_target_size: int       # 最终确定的目标
    resolved_soft_min: int         # 最终下限
    resolved_soft_max: int         # 最终上限
    current_projected_size: int    # 当前预计大小
    current_confidence: float      # 置信度
    source_policy_tier: str        # 来源分档
    updated_at: datetime
```

### ArcStructureDraft
```python
class ArcStructureDraft:
    arc_id: int
    key_beats: list[str]          # 关键节拍
    phase_layout: str              # 阶段布局
    thread_priorities: list[dict]  # 线程优先级
    hotspot_candidates: list[int] # 热点候选章节
    compression_candidates: list[int] # 可压缩章节
    created_at: datetime
```

### ArcEnvelopeAnalysis
```python
class ArcEnvelopeAnalysis:
    arc_id: int
    based_on_band_id: int
    recommendation: str            # keep / expand / compress
    evidence: str
    expansion_signals: list[str]
    compression_signals: list[str]
    suggested_target: int
    suggested_soft_min: int
    suggested_soft_max: int
    confidence: float
    created_at: datetime
```

### ProvisionalPromotionRecord
```python
class ProvisionalPromotionRecord:
    project_id: int
    arc_id: int
    band_id: int
    promoted_chapter_ids: list[int]
    promotion_reason: str
    based_on_analysis_id: int
    created_at: datetime
```

---

## 10. 分档示例

### 100 章小说
- 分档：短长篇
- base target：按 0.18 + clamp
- range：75% ~ 125%
- 每个 arc 都先 provisional 预演
- 最后确定 resolved envelope

### 1000 章小说
- 分档：超长连载
- base target：按 0.08 + clamp
- range：50% ~ 200%
- 每个 arc 仍然要 provisional 预演
- 不会因为是千章就跳过预演

---

## 11. 潜在问题与缓解

### 问题 1：成本上升
每个 arc 都要做 provisional 预演。

**缓解**：
- 只预演 current active arc
- shadow 只覆盖 current detailed band
- 不预演整本书

### 问题 2：range 太宽会偷懒
**缓解**：
- 必须同时使用 expansion/compression signals
- cooldown
- Pacing Strategist

### 问题 3：每个 arc 都预演太久会拖慢
**缓解**：
- 预演只做中层结构草案 + 近端 provisional band
- 不是写完整个 arc

---

## 12. 一句话版

> **v2.4 是一个"先用百分比 + 上下限得到基础 target，再按总篇幅分档决定 range，然后用 provisional 预演来确认每个 active arc 的最终 envelope"的长篇连载系统。**
