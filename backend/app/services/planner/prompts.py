"""Planner Service Prompts"""


PREMISE_ANALYSIS_PROMPT = """
请分析以下小说想法/剧情简述，提取核心元素并结构化输出：

{premise}

请分析并输出：
1. 类型/题材
2. 核心主题
3. 基调
4. 目标读者
5. 核心元素
6. 潜在冲突

请用简洁的语言回答。
"""


STORY_BIBLE_PROMPT = """
请根据以下信息为小说项目创建 Story Bible（故事圣经）：

项目标题: {project_title}
类型: {genre}
风格: {style}
剧情简述: {premise}

请创建包含以下内容的 Story Bible：
1. 故事主题
2. 一句话概述（Logline）
3. 故事大纲（Synopsis）
4. 世界观概述
5. 叙事结构
6. 核心冲突

请详细但简洁地描述每个部分。
"""


CHARACTER_CARD_PROMPT = """
请为以下小说项目创建 {count} 个角色卡：

项目标题: {project_title}
剧情简述: {premise}

每个角色卡需要包含：
1. 姓名
2. 角色类型（主角/配角/反派/次要）
3. 人物小传/背景
4. 性格特点
5. 核心动机/目标
6. 秘密（可选）
7. 人物关系

请确保角色有鲜明的个性，动机清晰，有发展潜力。
"""


ARC_PLAN_PROMPT = """
请为长篇小说项目规划故事弧线（Story Arc）：

项目标题: {project_title}
剧情简述: {premise}
总弧线数: {total_arcs}
每弧线目标章节数: {target_chapters_per_arc}

请为每个弧线规划：
1. 弧线标题
2. 弧线核心目标
3. 主要冲突
4. 预期章节数
5. 弧线摘要

确保弧线之间有递进关系，逐步推向故事高潮。
"""


CHAPTER_OUTLINE_PROMPT = """
请为小说项目生成章节大纲：

项目标题: {project_title}
剧情简述: {premise}
卷ID: {volume_id}
需要生成的大纲数量: {count}
起始章节号: {start_chapter_no}

已有的大纲摘要：
{existing_outlines}

请为每个章节生成：
1. 章节标题
2. 章节大纲（起承转合）
3. 章节钩子/悬念
4. 关键情节点

请确保：
- 章节之间有逻辑连贯性
- 节奏有起伏
- 每个章节都有明确的推进
- 设置合适的钩子吸引读者继续阅读
"""
