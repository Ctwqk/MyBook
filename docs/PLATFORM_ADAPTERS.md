# 国内网文平台适配指南

## 主要平台列表

| 平台 | 网址 | 特点 | 适配难度 |
|------|------|------|----------|
| 起点中文网 | https://www.qidian.com | 最大平台，会员体系完善 | ⭐⭐⭐⭐⭐ |
| 晋江文学城 | https://www.jjwxc.net | 女频为主，订阅制 | ⭐⭐⭐⭐ |
| 纵横中文网 | https://www.zongheng.com | 老牌平台 | ⭐⭐⭐⭐ |
| 飞卢小说网 | https://www.faloo.com | 订阅+打赏 | ⭐⭐⭐ |
| 创世中文网 | https://chuangshi.qq.com | 腾讯系 | ⭐⭐⭐⭐ |
| 17K小说网 | https://www.17k.com | 多种合作模式 | ⭐⭐⭐ |
| 红袖添香 | https://www.hongxiu.com | 女频 | ⭐⭐⭐ |
| 潇湘书院 | https://www.xxssy.com | 女频 | ⭐⭐⭐ |
| 番茄小说 | https://fanqienovel.com | 免费+广告 | ⭐⭐⭐ |
| 七猫小说 | https://www.qimao.com | 免费为主 | ⭐⭐ |
| 咪咕阅读 | https://www.migu.cn | 移动系 | ⭐⭐⭐ |
| 百度小说 | https://yuedu.baidu.com | 百度系 | ⭐⭐⭐ |

## 适配器基类

```python
from abc import ABC, abstractmethod
from typing import Optional, Any
import httpx

class BaseNovelPlatform(ABC):
    """网文平台基类"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    @abstractmethod
    async def login(self, username: str, password: str) -> dict[str, Any]:
        """登录"""
        pass
    
    @abstractmethod
    async def create_book(self, book_info: dict) -> dict[str, Any]:
        """创建书籍"""
        pass
    
    @abstractmethod
    async def publish_chapter(self, book_id: str, chapter_info: dict) -> dict[str, Any]:
        """发布章节"""
        pass
    
    @abstractmethod
    async def get_book_info(self, book_id: str) -> dict[str, Any]:
        """获取书籍信息"""
        pass
    
    async def close(self):
        await self.client.aclose()
```

## 通用错误码

```python
class PlatformErrorCode:
    # 登录错误
    LOGIN_FAILED = "LOGIN_FAILED"           # 登录失败
    LOGIN_CAPTCHA = "LOGIN_CAPTCHA"         # 需要验证码
    LOGIN_LOCKED = "LOGIN_LOCKED"           # 账户被锁
    PASSWORD_ERROR = "PASSWORD_ERROR"       # 密码错误
    
    # 发布错误
    TITLE_TOO_SHORT = "TITLE_TOO_SHORT"     # 书名太短
    CONTENT_TOO_SHORT = "CONTENT_TOO_SHORT" # 内容太短
    CHAPTER_EXISTS = "CHAPTER_EXISTS"       # 章节已存在
    BOOK_NOT_APPROVED = "BOOK_NOT_APPROVED" # 书籍未审核通过
    
    # 通用错误
    SESSION_EXPIRED = "SESSION_EXPIRED"     # 会话过期
    RATE_LIMITED = "RATE_LIMITED"           # 请求限流
    NETWORK_ERROR = "NETWORK_ERROR"         # 网络错误
    UNKNOWN_ERROR = "UNKNOWN_ERROR"         # 未知错误
```

## TODO: 各平台适配器实现

### 1. 起点中文网 (QidianAdapter)
```python
# TODO: 实现起点中文网适配器
# - 需要处理复杂的登录流程（含验证码）
# - 创世中文网使用同一账号体系
# class QidianAdapter(BaseNovelPlatform):
#     async def login(...): pass
#     async def create_book(...): pass
#     async def publish_chapter(...): pass
```

### 2. 晋江文学城 (JjwxcAdapter)
```python
# TODO: 实现晋江适配器
# - 登录需要处理 Cookie
# - 订阅制需要注意订阅比例
# class JjwxcAdapter(BaseNovelPlatform):
#     async def login(...): pass
```

### 3. 其他平台
```python
# TODO: 纵横中文网 -> class ZongHengAdapter
# TODO: 飞卢小说网 -> class FalooAdapter
# TODO: 创世中文网 -> class ChuangShiAdapter
# TODO: 17K小说网 -> class SeventeenKAdapter
# TODO: 红袖添香 -> class HongXiuAdapter
# TODO: 潇湘书院 -> class XiaoXiangAdapter
# TODO: 番茄小说 -> class FanQieAdapter
# TODO: 七猫小说 -> class QiMaoAdapter
# TODO: 咪咕阅读 -> class MiGuAdapter
```

## 重要提示

⚠️ **合法性提醒**：
1. 大多数平台的自动发布可能违反其服务条款
2. 建议仅用于个人备份和测试
3. 商业使用请与平台方联系合作
4. 请遵守robots.txt和服务条款

⚠️ **技术风险**：
1. 平台会持续更新反爬机制
2. 登录验证可能包含验证码、人机验证
3. 需要处理 IP 限制、请求频率限制
4. Cookie/Session 可能定期失效

## 实现建议

1. **使用 Playwright/Selenium** 处理复杂登录
2. **实现重试机制** 处理临时失败
3. **定期更新** Cookie 和 Token
4. **实现代理池** 避免 IP 被封
5. **添加人工验证** 处理复杂验证码

## 待开发清单

- [ ] QidianAdapter - 起点中文网
- [ ] JjwxcAdapter - 晋江文学城
- [ ] ZongHengAdapter - 纵横中文网
- [ ] FalooAdapter - 飞卢小说网
- [ ] ChuangShiAdapter - 创世中文网
- [ ] SeventeenKAdapter - 17K小说网
- [ ] HongXiuAdapter - 红袖添香
- [ ] XiaoXiangAdapter - 潇湘书院
- [ ] FanQieAdapter - 番茄小说
- [ ] QiMaoAdapter - 七猫小说
- [ ] MiGuAdapter - 咪咕阅读
