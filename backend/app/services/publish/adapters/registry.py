"""
平台适配器注册表
"""
from typing import Type, Dict, TypeVar, Any

from app.services.publish.adapter import PlatformAdapter, MockPlatformAdapter
from app.services.publish.adapters.qidian import QidianAdapter
from app.services.publish.adapters.jjwxc import JjwxcAdapter
from app.services.publish.adapters.fanqie import FanQieAdapter

# 适配器注册表
ADAPTER_REGISTRY: Dict[str, Type[PlatformAdapter]] = {
    "mock": MockPlatformAdapter,
    "qidian": QidianAdapter,
    "jjwxc": JjwxcAdapter,
    "fanqie": FanQieAdapter,
}

# 平台元数据
PLATFORM_INFO = {
    "mock": {
        "name": "Mock (测试)",
        "description": "用于开发测试的模拟适配器",
        "features": ["登录", "创建书籍", "发布章节", "保存草稿", "删除章节"],
        "requires_browser": False,
        "requires_credentials": False,
    },
    "qidian": {
        "name": "起点中文网",
        "description": "阅文集团旗下最大网文平台，支持VIP订阅、打赏等功能",
        "features": [
            "账号登录/Cookie登录",
            "创建书籍",
            "发布章节",
            "保存草稿",
            "删除章节",
            "获取书籍列表",
            "获取章节列表",
            "获取分类信息",
        ],
        "requires_browser": False,
        "requires_credentials": True,
        "website": "https://www.qidian.com",
        "author_portal": "https://creator.qidian.com",
        "genre_options": [
            "玄幻", "奇幻", "武侠", "仙侠", "都市", "职场",
            "军事", "历史", "游戏", "竞技", "科幻", "灵异",
            "悬疑", "轻小说", "二次元", "女生网"
        ],
        "notes": "创世中文网使用同一账号体系",
    },
    "jjwxc": {
        "name": "晋江文学城",
        "description": "知名女频网文平台，订阅制为主",
        "features": [
            "账号登录/Cookie登录",
            "创建书籍",
            "发布章节(含VIP/免费)",
            "保存草稿",
            "删除章节",
            "获取书籍列表",
            "获取章节列表",
            "订阅比例设置",
        ],
        "requires_browser": False,
        "requires_credentials": True,
        "website": "https://www.jjwxc.net",
        "author_portal": "https://www.jjwxc.net/mine.php",
        "genre_options": [
            "现代都市", "穿越重生", "玄幻奇幻", "星际科幻",
            "武侠仙侠", "悬疑推理", "游戏竞技", "NPH", "GB",
            "百合", "无CP", "衍生同人"
        ],
        "notes": "女频为主，订阅分成制",
    },
    "fanqie": {
        "name": "番茄小说",
        "description": "字节跳动旗下免费阅读平台，广告分成模式",
        "features": [
            "账号登录/短信登录/Token登录",
            "创建书籍",
            "发布章节",
            "保存草稿",
            "删除章节",
            "获取书籍列表",
            "获取章节列表",
            "Token自动刷新",
        ],
        "requires_browser": False,
        "requires_credentials": True,
        "website": "https://fanqienovel.com",
        "author_portal": "https://author.fanqienovel.com",
        "genre_options": [
            "都市", "玄幻", "仙侠", "武侠", "奇幻", "科幻",
            "游戏", "悬疑", "灵异", "轻小说", "短篇", "现实",
            "军事", "历史", "体育"
        ],
        "notes": "免费+广告分成模式，面向免费阅读",
    },
}


def get_adapter_class(platform: str) -> Type[PlatformAdapter]:
    """获取适配器类"""
    adapter_class = ADAPTER_REGISTRY.get(platform.lower())
    if adapter_class is None:
        available = list(ADAPTER_REGISTRY.keys())
        raise ValueError(f"Unknown platform: {platform}. Available: {available}")
    return adapter_class


def create_adapter(platform: str) -> PlatformAdapter:
    """创建适配器实例"""
    adapter_class = get_adapter_class(platform)
    return adapter_class()


def list_platforms() -> Dict[str, Dict[str, Any]]:
    """列出所有可用平台"""
    return PLATFORM_INFO.copy()


def get_platform_info(platform: str) -> Dict[str, Any]:
    """获取平台详情"""
    info = PLATFORM_INFO.get(platform.lower())
    if info is None:
        raise ValueError(f"Unknown platform: {platform}")
    return info


# 导出
__all__ = [
    "ADAPTER_REGISTRY",
    "PLATFORM_INFO",
    "get_adapter_class",
    "create_adapter",
    "list_platforms",
    "get_platform_info",
    "MockPlatformAdapter",
    "QidianAdapter",
    "JjwxcAdapter",
    "FanQieAdapter",
]
