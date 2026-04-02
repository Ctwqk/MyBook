"""Writer Service Prompts - v2.3 Scene 模式

支持：
- 单章单次生成
- 分 scene 生成 + stitch
- 结构化输出
- 错误恢复
"""

# ========================================
# Scene Breakdown - 将章节拆分成 scenes
# ========================================

SCENE_BREAKDOWN_PROMPT = """
请将小说第 {chapter_no} 章拆分成 {scene_count} 个 scenes。

【重要】输出要求：
1. 只输出 scene 计划，不要输出任何思考过程
2. 每个 scene 包含：scene_no、scene_objective、scene_time_point、scene_location、involved_entities、must_progress_points、micro_hook

章节信息：
- 章节号：{chapter_no}
- 标题：{title}
- 大纲：
{outline}

上下文：
{context}

请输出 {scene_count} 个 scene 的详细计划。
"""


# ========================================
# Scene Generation - 单个 scene 生成
# ========================================

SCENE_GENERATION_PROMPT = """
请创作小说第 {chapter_no} 章的第 {scene_no}/{total_scenes} 个 scene。

【重要】输出要求：
1. 只输出 scene 正文，不要输出任何思考过程、注释或元信息
2. 不要在正文中包含 "<think>"、"起："、"承："、"转："、"合：" 等标记
3. scene 以 scene 标题开头，如 "【Scene {scene_no}】"

Scene 信息：
- Scene 编号：{scene_no}/{total_scenes}
- Scene 目标：{scene_objective}
- 时间点：{scene_time_point}
- 地点：{scene_location}
- 参与角色：{involved_entities}
- 必须推进点：{must_progress_points}
- 结尾微钩子：{micro_hook}

前序 scene 结尾：
{previous_scene_ending}

请创作这个 scene，保持文笔流畅，情节紧凑。
Scene 目标字数：约 {target_words} 字。
"""


# ========================================
# Scene Stitch - 合并 scenes 成章节
# ========================================

SCENE_STITCH_PROMPT = """
请将 {scene_count} 个 scenes 合并成完整的章节，并进行轻量润色。

【重要】输出要求：
1. 只输出合并后的章节正文，不要输出任何思考过程
2. 检查并确保：
   - scene 之间衔接自然
   - 人称/文风一致
   - 时间/地点连贯
   - 章末 hook 到位
3. 可以做轻量润色，但不要大篇幅重写

Scenes：
{scenes}

章节信息：
- 章节号：{chapter_no}
- 标题：{title}
- 大纲：
{outline}

请输出合并后的完整章节。
"""


# ========================================
# Structured Extraction - 从章节中提取结构化信息
# ========================================

STRUCTURED_EXTRACTION_PROMPT = """
请从以下章节中提取结构化信息。

【重要】输出要求：
1. 只输出结构化信息，不要输出任何思考过程
2. 以 JSON 格式输出

章节内容：
{chapter_text}

请提取并输出：
1. chapter_summary：章节摘要（100字以内）
2. event_candidates：本章重要事件列表
3. state_change_candidates：角色状态变化列表
4. thread_beat_candidates：伏笔/悬念推进列表
5. lore_candidates：世界观细节列表
6. timeline_hints：时间线提示

请以 JSON 格式输出。
"""


# ========================================
# 单章生成（兼容旧模式，阶段 0.5 使用）
# ========================================

CHAPTER_GENERATION_PROMPT = """
请为小说项目生成第 {chapter_no} 章的正文。

【重要】输出要求：
1. 只输出小说正文，不要输出任何思考过程、注释或元信息
2. 不要在正文中包含"<think>"、"## 大纲"、"起："、"承："、"转："、"合："等标记
3. 正文章节以章节标题开头，如 "# 第{chapter_no}章：{title}"

章节信息：
- 章节号：{chapter_no}
- 标题：{title}
- 大纲：
{outline}

故事上下文：
{context}

{style_hints}

请创作引人入胜的小说章节。保持文笔流畅，情节紧凑。
章节长度建议在 2000-4000 字之间。
"""


# ========================================
# 续写章节
# ========================================

CHAPTER_CONTINUATION_PROMPT = """
请续写小说第 {chapter_no} 章。

【重要】输出要求：
1. 只输出续写内容，不要输出任何思考过程
2. 保持与已有内容的风格一致

已有内容：
{existing_text}

最后一段内容：
{last_paragraph}

故事上下文：
{context}

目标字数：约 {target_word_count} 字

请继续创作，保持文风一致，情节自然衔接。
"""


# ========================================
# 重写章节
# ========================================

CHAPTER_REWRITE_PROMPT = """
请重写小说第 {chapter_no} 章。

【重要】输出要求：
1. 只输出重写后的正文，不要输出任何思考过程或注释

原内容：
{existing_text}

修改指令：
{rewrite_instructions}

故事上下文：
{context}

请按照修改指令重写章节，保持核心情节不变。
"""


# ========================================
# 修补章节段落
# ========================================

CHAPTER_PATCH_PROMPT = """
请修补小说第 {chapter_no} 章中的特定段落。

【重要】输出要求：
1. 只输出修补后的段落内容，不要输出任何思考过程

章节内容：
{existing_text}

需要修补的段落：
{segment_content}

修补指令：
{patch_instructions}

请只输出修补后的段落内容。
"""


# ========================================
# 降级提取（当结构化输出失败时使用）
# ========================================

FALLBACK_EXTRACTION_PROMPT = """
请从以下章节中提取基本信息（降级模式）。

【重要】输出要求：
1. 只输出摘要，不要输出任何思考过程

章节内容：
{chapter_text}

请输出：
1. 章节摘要（50字以内）
2. 主要事件（3个以内）
"""


# ========================================
# 错误恢复时的 Repair Prompt
# ========================================

WRITER_REPAIR_PROMPT = """
请重新生成第 {chapter_no} 章的正文（修复版本）。

【重要】输出要求：
1. 只输出小说正文，不要输出任何思考过程
2. 不要在正文中包含大纲标记

原生成问题：
{original_error}

修复要求：
{repair_instructions}

章节信息：
- 章节号：{chapter_no}
- 标题：{title}
- 大纲：
{outline}

上下文：
{context}

请重新生成章节，确保：
1. 修复之前的问题
2. 保持文笔流畅
3. 情节完整

目标字数：约 {target_word_count} 字。
"""
