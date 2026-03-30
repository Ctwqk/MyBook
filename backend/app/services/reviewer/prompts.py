"""Reviewer Service Prompts"""


CHAPTER_REVIEW_PROMPT = """
请审查以下小说章节：

章节信息：
- 章节号：{chapter_no}
- 标题：{title}
- 大纲：{outline}

章节正文：
{text}

故事上下文：
{context}

请重点检查以下方面：{check_types}

请从以下维度进行评估：
1. 一致性检查 - 角色设定、世界观、情节逻辑是否一致
2. 节奏检查 - 情节推进是否流畅，是否有拖沓或过于仓促
3. 钩子检查 - 章节开头和结尾是否有吸引读者的钩子
4. 大纲完成度 - 是否按照章节大纲推进

请给出：
1. 总评分（0-10）
2. 主要优点
3. 发现的问题（按严重程度排序）
4. 总体评价

请用结构化格式输出。
"""


PARTIAL_REVIEW_PROMPT = """
请审查以下小说段落：

段落位置：{segment_location}

段落内容：
{segment_text}

请检查以下方面：{check_types}

请简要评价：
1. 优点
2. 问题
3. 改进建议

请简洁回答。
"""


REWRITE_INSTRUCTIONS_PROMPT = """
请根据以下审查问题，为小说第 {chapter_no} 章生成重写指令。

审查问题列表：
{issues}

当前章节内容（部分）：
{existing_text}

请生成清晰、可执行的重写指令，包括：
1. 主要修改方向
2. 具体修改点
3. 保持不变的部分
4. 优先级排序

请用结构化格式输出。
"""
