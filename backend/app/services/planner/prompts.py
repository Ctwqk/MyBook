"""Planner Service Prompts"""

PREMISE_ANALYSIS_PROMPT = """
请分析故事前提，提取核心要素。

故事概述：
{synopsis}

请提取并输出：
1. 核心主题
2. 主要冲突
3. 关键角色类型
4. 故事基调

请用结构化格式输出。
"""

STORY_BIBLE_PROMPT = """
请为小说项目创建故事设定。

【重要】输出要求：
1. 只输出故事设定内容，不要输出任何思考过程
2. 设定内容要详细、完整

类型：{genre}
主题：{theme}
基调：{tone}
概述：{synopsis}

请输出完整的故事设定文档。
"""

CHARACTER_CARD_PROMPT = """
请为小说角色创建角色卡。

【重要】输出要求：
1. 只输出角色卡内容，不要输出任何思考过程
2. 角色信息要详细、生动

角色名称：{name}
角色类型：{role_type}

请创建角色卡。
"""

ARC_PLAN_PROMPT = """
请规划故事线的起承转合。

【重要】输出要求：
1. 只输出故事线规划，不要输出任何思考过程
2. 确保情节递进合理

故事主题：{theme}
总章节数：{total_chapters}

请规划故事线。
"""

CHAPTER_OUTLINE_PROMPT = """
请为小说项目的第 {chapter_no} 章创作详细大纲。

【重要】输出要求：
1. 只输出章节大纲内容，不要输出任何思考过程
2. 大纲格式清晰，使用"起、承、转、合"结构
3. 最后可加"钩子"用于吸引读者继续阅读

故事信息：
- 项目类型：{genre}
- 故事主题：{theme}
- 故事基调：{tone}
- 故事概述：{synopsis}

前几章概要：
{previous_chapters}

章节要求：
- 章节号：{chapter_no}
- 章节标题：{title}

请创作章节大纲。
"""

CHAPTER_BATCH_OUTLINE_PROMPT = """
请为小说项目规划 {total_chapters} 章的大纲。

【重要】输出要求：
1. 只输出章节大纲列表，不要输出任何思考过程
2. 每章大纲使用"起、承、转、合"结构
3. 确保章节之间情节连贯，伏笔铺设合理

故事信息：
- 项目类型：{genre}
- 故事主题：{theme}
- 故事基调：{tone}
- 故事概述：{synopsis}

请规划 {total_chapters} 章的大纲。
"""

CHAPTER_REVISION_PROMPT = """
请修改第 {chapter_no} 章的大纲。

【重要】输出要求：
1. 只输出修改后的章节大纲，不要输出任何思考过程

原大纲：
{original_outline}

修改要求：
{revision_request}

请输出修改后的大纲。
"""
