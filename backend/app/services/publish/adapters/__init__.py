"""
网文平台适配器

本模块包含国内主要网文平台的完整适配器实现。

平台列表：
- mock: Mock 适配器 (测试用)
- qidian: 起点中文网
- jjwxc: 晋江文学城
- fanqie: 番茄小说

使用示例：
```python
from app.services.publish.adapters import create_adapter, list_platforms

# 列出所有平台
platforms = list_platforms()

# 创建适配器
adapter = create_adapter("qidian")

# 登录
await adapter.login("username", "password")

# 创建书籍
result = await adapter.create_book("书名", "玄幻", "简介")

# 发布章节
result = await adapter.publish_chapter(
    book_id="123456",
    chapter_no=1,
    title="第一章",
    content="章节内容..."
)
```
"""
from app.services.publish.adapter import PlatformAdapter, MockPlatformAdapter
from app.services.publish.adapters.registry import (
    ADAPTER_REGISTRY,
    PLATFORM_INFO,
    get_adapter_class,
    create_adapter,
    list_platforms,
    get_platform_info,
)

# 导入所有适配器
from app.services.publish.adapters.qidian import QidianAdapter, QidianAPIError
from app.services.publish.adapters.jjwxc import JjwxcAdapter, JjwxcAPIError
from app.services.publish.adapters.fanqie import FanQieAdapter, FanQieAPIError

__all__ = [
    # 基类
    "PlatformAdapter",
    "MockPlatformAdapter",
    
    # 适配器
    "QidianAdapter",
    "JjwxcAdapter",
    "FanQieAdapter",
    
    # 异常
    "QidianAPIError",
    "JjwxcAPIError",
    "FanQieAPIError",
    
    # 注册表
    "ADAPTER_REGISTRY",
    "PLATFORM_INFO",
    "get_adapter_class",
    "create_adapter",
    "list_platforms",
    "get_platform_info",
]
