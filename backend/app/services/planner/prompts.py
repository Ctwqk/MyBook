PREMISE_ANALYSIS_PROMPT = """
请分析以下小说想法，提取核心元素：

{premise}

请输出JSON格式：
{{"genre":"类型","theme":"主题","tone":"基调","target_audience":"目标读者","key_elements":["关键元素1","关键元素2"],"potential_conflicts":["潜在冲突1","潜在冲突2"]}}
"""

STORY_BIBLE_PROMPT = """
为小说项目创建Story Bible：

项目标题: {project_title}
剧情简述: {premise}
类型: {genre}
风格: {style}

请生成：
1. 世界观设定（200字）
2. 主题探讨（100字）
3. 主要角色设定（每个150字）
4. 故事弧线概述（200字）

直接输出内容，不需要特殊格式。
"""

CHARACTER_CARD_PROMPT = """
为"{project_title}"项目生成{count}个角色：

剧情：{premise}

请为每个角色输出：
- 姓名：
- 角色类型（主角/反派/配角）：
- 背景：
- 性格特点：
- 动机：
- 秘密/隐藏面：

直接输出即可。
"""

ARC_PLAN_PROMPT = """
为"{project_title}"项目规划{total_arcs}个故事弧线：

剧情：{premise}
每个弧线目标章节数：{target_chapters_per_arc}

请为每个弧线输出：
- 弧线编号和标题
- 弧线目标
- 主要冲突
- 预期章节数

直接输出即可。
"""

CHAPTER_OUTLINE_PROMPT = """
请为小说项目生成{count}个章节大纲。

项目标题: {project_title}
剧情简述: {premise}
起始章节号: {start_chapter_no}

请为每个章节生成简洁大纲，格式如下（每个章节50-100字）：

章节{start_chapter_no}：
起：xxx
承：xxx
转：xxx
合：xxx
钩子：xxx

章节2：
起：xxx
承：xxx
转：xxx
合：xxx
钩子：xxx

（继续直到第{count}章，每章格式相同）

注意：
- 每个章节大纲控制在50-100字
- 确保章节之间有逻辑连贯
- 钩子要能吸引读者
"""
