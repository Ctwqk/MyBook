"""Reviewer Service Prompts - v2.3 结构化输出 + 错误恢复

支持：
- 结构化 JSON 输出
- ReviewVerdict 解析失败重试
- 降级到 rule-based 检查
"""

# ========================================
# 章节审查 - 结构化输出
# ========================================

CHAPTER_REVIEW_PROMPT = """
请审查小说第 {chapter_no} 章的质量。

【重要】输出要求：
1. 只输出审查结果，不要输出任何思考过程
2. 必须使用 JSON 格式输出

章节信息：
- 章节号：{chapter_no}
- 标题：{title}
- 大纲：{outline}

章节正文：
{chapter_text}

上下文：
{context}

审查标准（{check_types}）：
1. 情节连贯性 - consistency
2. 节奏控制 - pacing  
3. 章末钩子 - hook
4. 人物塑造 - character
5. 文笔质量 - style

请以 JSON 格式输出：
{{
    "verdict": "pass/patch_required/rewrite_required/blocked",
    "verdict_reason": "判定理由",
    "issues": [
        {{
            "issue_type": "consistency/pacing/hook/character/style",
            "location": "问题位置描述",
            "description": "问题描述",
            "severity": "critical/major/minor",
            "fix_suggestion": "修复建议"
        }}
    ],
    "scores": {{
        "consistency": 0.0-1.0,
        "pacing": 0.0-1.0,
        "hook": 0.0-1.0,
        "character": 0.0-1.0,
        "style": 0.0-1.0,
        "overall": 0.0-1.0
    }},
    "patch_instructions": "修补指令（如需）",
    "rewrite_instructions": "重写指令（如需）"
}}
"""

# ========================================
# 部分审查
# ========================================

PARTIAL_REVIEW_PROMPT = """
请审查小说章节的特定段落。

【重要】输出要求：
1. 只输出审查结果，不要输出任何思考过程
2. 必须使用 JSON 格式输出

需要审查的段落：
{segment_text}

位置：{segment_location}

审查标准（{check_types}）：
1. 连贯性 - consistency
2. 节奏 - pacing
3. 人物 - character
4. 文笔 - style

请以 JSON 格式输出：
{{
    "verdict": "pass/needs_patch",
    "verdict_reason": "判定理由",
    "issues": [
        {{
            "issue_type": "string",
            "location": "string",
            "description": "string",
            "severity": "critical/major/minor",
            "fix_suggestion": "string"
        }}
    ],
    "scores": {{
        "consistency": 0.0-1.0,
        "pacing": 0.0-1.0,
        "overall": 0.0-1.0
    }}
}}
"""


# ========================================
# 生成重写指令
# ========================================

REWRITE_INSTRUCTIONS_PROMPT = """
请根据审查意见生成重写指令。

【重要】输出要求：
1. 只输出重写指令，不要输出任何思考过程
2. 必须使用 JSON 格式输出

章节号：{chapter_no}

原内容摘要：
{existing_text}

审查问题列表：
{issues}

请生成清晰、可执行的重写指令，以 JSON 格式输出：
{{
    "rewrite_instructions": "具体的重写指令",
    "prioritized_fixes": ["优先修复项1", "优先修复项2"],
    "keep_elements": ["必须保留的元素"],
    "tone_guidance": "语调指导"
}}
"""


# ========================================
# 降级审查（ReviewVerdict 解析失败时使用）
# ========================================

FALLBACK_REVIEW_PROMPT = """
请进行最简规则审查（降级模式）。

【重要】输出要求：
1. 只输出审查结果，不要输出任何思考过程
2. 必须使用 JSON 格式输出

章节正文：
{chapter_text}

请检查以下最基本规则：
1. 是否有明显错别字或病句
2. 是否有明显的时间/地点矛盾
3. 章节是否有开头和结尾

请以 JSON 格式输出：
{{
    "verdict": "pass/needs_patch",
    "verdict_reason": "简要理由",
    "basic_issues": ["基本问题1", "基本问题2"],
    "can_proceed": true/false
}}
"""


# ========================================
# 审查修复后重审
# ========================================

REVIEW_REVISION_PROMPT = """
请重新审查修改后的章节。

【重要】输出要求：
1. 只输出审查结果，不要输出任何思考过程
2. 必须使用 JSON 格式输出

章节信息：
- 章节号：{chapter_no}
- 标题：{title}

原审查问题：
{previous_issues}

修改后的正文：
{revised_text}

请检查：
1. 原问题是否已修复
2. 是否有新问题

请以 JSON 格式输出：
{{
    "verdict": "pass/needs_further_revision",
    "verdict_reason": "判定理由",
    "fixed_issues": ["已修复问题列表"],
    "remaining_issues": ["仍存在的问题"],
    "new_issues": ["新发现的问题"],
    "scores": {{
        "consistency": 0.0-1.0,
        "pacing": 0.0-1.0,
        "overall": 0.0-1.0
    }}
}}
"""


# ========================================
# 版本对比
# ========================================

CHAPTER_COMPARISON_PROMPT = """
请对比两个版本的章节，给出选择建议。

【重要】输出要求：
1. 只输出对比结果，不要输出任何思考过程
2. 必须使用 JSON 格式输出

版本1：
{version1}

版本2：
{version2}

请以 JSON 格式输出：
{{
    "recommended_version": "1/2/both_needs_work",
    "reason": "推荐理由",
    "version1_strengths": ["优势列表"],
    "version1_weaknesses": ["劣势列表"],
    "version2_strengths": ["优势列表"],
    "version2_weaknesses": ["劣势列表"],
    "merged_recommendation": "是否建议合并两者优点"
}}
"""


# ========================================
# v2.7: 修复重写提示
# ========================================

WRITER_REPAIR_PROMPT = """
请根据修复指令重写章节。

【重要】输出要求：
1. 只输出重写后的章节内容，不要输出任何解释
2. 严格按照修复指令执行
3. 保留必须保留的元素

章节信息：
- 章节号：{chapter_no}
- 标题：{title}

修复范围：{repair_scope}（scene=仅当前章节，band=当前章节+Band级别调整，arc=当前章节+Arc级别调整）

必须修复的问题：
{must_fix}

必须保留的元素：
{must_preserve}

现有章节内容：
{existing_text}

请重写章节，确保：
1. 修复所有必须修复的问题
2. 保留所有必须保留的元素
3. 保持情节连贯性和人物一致性
4. 提升读者体验

只需输出重写后的完整章节正文。
"""
