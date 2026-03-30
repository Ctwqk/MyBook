"""Writer Service Prompts"""


CHAPTER_GENERATION_PROMPT = """
请为小说项目生成第 {chapter_no} 章的正文。

章节信息：
- 章节号：{chapter_no}
- 标题：{title}
- 大纲：
{outline}

故事上下文：
{context}

{style_hints}

请根据以上信息，创作引人入胜的小说章节。保持文笔流畅，情节紧凑。
章节长度建议在 2000-4000 字之间。
"""


CHAPTER_CONTINUATION_PROMPT = """
请续写小说第 {chapter_no} 章。

已有内容：
{existing_text}

最后一段内容：
{last_paragraph}

故事上下文：
{context}

目标字数：约 {target_word_count} 字

请继续创作，保持文风一致，情节自然衔接。
"""


CHAPTER_REWRITE_PROMPT = """
请重写小说第 {chapter_no} 章。

原内容：
{existing_text}

修改指令：
{rewrite_instructions}

故事上下文：
{context}

请按照修改指令重写章节，保持核心情节不变，但改进指定问题。
"""


CHAPTER_PATCH_PROMPT = """
请修补小说第 {chapter_no} 章中的特定段落。

章节内容：
{existing_text}

需要修补的段落：
{segment_content}

修补指令：
{patch_instructions}

请只输出修补后的段落内容，不要输出其他内容。
"""


CHAPTER_EXTRACTION_PROMPT = """
请分析以下小说章节内容，提取关键信息：

章节号：{chapter_no}

章节内容：
{text}

请提取并输出：
1. 章节摘要（100字以内）
2. 角色状态变化（列出发生变化的角色和变化内容）
3. 伏笔变化（列出新埋下的伏笔和已有伏笔的进展）

请用结构化格式输出。
"""
