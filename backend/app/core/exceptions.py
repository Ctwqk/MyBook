"""自定义异常"""


class MyBookException(Exception):
    """基础异常"""
    pass


class ProjectNotFoundError(MyBookException):
    """项目不存在"""
    pass


class ChapterNotFoundError(MyBookException):
    """章节不存在"""
    pass


class CharacterNotFoundError(MyBookException):
    """角色不存在"""
    pass


class LLMProviderError(MyBookException):
    """LLM provider 错误"""
    pass


class GenerationError(MyBookException):
    """生成错误"""
    pass


class ReviewError(MyBookException):
    """审查错误"""
    pass


class PublishError(MyBookException):
    """发布错误"""
    pass


class MemoryError(MyBookException):
    """记忆错误"""
    pass
