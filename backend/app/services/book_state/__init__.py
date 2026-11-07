"""BookState Service - 世界状态运行时

核心组件：
- BookStateRuntime: 世界状态运行时
- GraphDeltaCompiler: 增量编译器
- BookStateRepository: 数据访问层
"""
from app.services.book_state.runtime import BookStateRuntime
from app.services.book_state.compiler import GraphDeltaCompiler
from app.services.book_state.repository import BookStateRepository

__all__ = [
    "BookStateRuntime",
    "GraphDeltaCompiler", 
    "BookStateRepository",
]