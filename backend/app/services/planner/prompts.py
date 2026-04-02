"""Planner Service Prompts"""

PREMISE_ANALYSIS_PROMPT = """
请分析故事前提，提取核心要素。

故事概述：
{premise}

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

项目名称：{project_title}
剧情简述：{premise}
类型：{genre}
风格：{style}

请输出完整的故事设定文档。
"""

CHARACTER_CARD_PROMPT = """
请为小说项目创建角色。

【重要】输出要求：
1. 只输出角色信息，不要输出任何思考过程
2. 角色信息要详细、生动

项目名称：{project_title}
剧情简述：{premise}
需要创建的角色数量：{count}

请为这个故事创建 {count} 个角色，包括主角、配角和反派。每个角色需要有：
- 姓名
- 类型（主角/配角/反派）
- 背景故事
- 性格特点
- 在故事中的作用
"""

ARC_PLAN_PROMPT = """
请为小说项目规划故事弧线。

【重要】输出要求：
1. 只输出故事弧线规划，不要输出任何思考过程
2. 确保情节递进合理

项目名称：{project_title}
剧情简述：{premise}
总弧线数：{total_arcs}
每弧线目标章节数：{target_chapters_per_arc}

请将故事分为 {total_arcs} 个弧线，每个弧线包含约 {target_chapters_per_arc} 章。
"""

CHAPTER_OUTLINE_PROMPT = """
请为小说项目规划章节大纲。

【重要】输出要求：
1. 只输出章节大纲，不要输出任何思考过程
2. 每章大纲使用"起、承、转、合"结构

项目名称：{project_title}
剧情简述：{premise}
起始章节号：{start_chapter_no}
结束章节号：{end_chapter_no}
卷ID（可选）：{volume_id}

已有大纲：
{existing_outlines}

请为第 {start_chapter_no} 章到第 {end_chapter_no} 章创建大纲。
"""

CHAPTER_BATCH_OUTLINE_PROMPT = """
请为小说项目规划章节大纲。

【重要】输出要求：
1. 只输出章节大纲列表，不要输出任何思考过程
2. 每章大纲使用"起、承、转、合"结构

项目名称：{project_title}
剧情简述：{premise}
总章节数：{total_chapters}

请规划 {total_chapters} 章的大纲。
"""

CHAPTER_REVISION_PROMPT = """
请修改章节大纲。

【重要】输出要求：
1. 只输出修改后的大纲，不要输出任何思考过程

章节号：{chapter_no}
原大纲：
{original_outline}

修改要求：
{revision_request}

请输出修改后的大纲。
"""
