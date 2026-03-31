"""Reviewer Service Prompts"""

CHAPTER_REVIEW_PROMPT = """
请审查小说第 {chapter_no} 章的质量。

【重要】输出要求：
1. 只输出审查结果，不要输出任何思考过程
2. 使用 JSON 格式输出审查结果

章节内容：
{chapter_text}

审查标准：
1. 情节连贯性
2. 人物塑造
3. 文笔质量
4. 伏笔铺设
5. 整体可读性

请给出：
- 评分（1-10）
- 优点
- 改进建议
"""

PARTIAL_REVIEW_PROMPT = """
请审查小说章节的特定段落。

【重要】输出要求：
1. 只输出审查结果，不要输出任何思考过程

章节内容：
{chapter_text}

需要审查的段落：
{segment_content}

请分析该段落的质量并给出改进建议。
"""

REWRITE_INSTRUCTIONS_PROMPT = """
请根据审查意见生成重写指令。

【重要】输出要求：
1. 只输出重写指令，不要输出任何思考过程

原内容：
{original_text}

审查意见：
{review_comments}

请生成具体的重写指令。
"""

CHAPTER_COMPARISON_PROMPT = """
请对比两个版本的章节，给出选择建议。

【重要】输出要求：
1. 只输出对比结果，不要输出任何思考过程
2. 使用 JSON 格式输出

版本1：
{version1}

版本2：
{version2}

请分析两个版本的优劣，并给出推荐。
"""
