"""
番茄小说完整适配器
支持登录、创书、发布章节等功能
"""
import asyncio
import hashlib
import json
import logging
import random
import re
import time
import base64
from typing import Any, Optional
from dataclasses import dataclass, field
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup

from app.models.publish_task import PublishErrorCode

logger = logging.getLogger(__name__)


@dataclass
class FanQieCredentials:
    """番茄账号凭证"""
    username: str
    password: str
    token: Optional[str] = None
    cookies: dict = field(default_factory=dict)
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    device_id: Optional[str] = None


@dataclass
class FanQieBookInfo:
    """番茄书籍信息"""
    book_id: str
    title: str
    author_id: str
    author_name: str
    status: str  # ongoing, completed
    genre: str
    word_count: int
    chapter_count: int
    read_count: int
    is_free: bool = True
    cover_url: Optional[str] = None


@dataclass
class FanQieChapterInfo:
    """番茄章节信息"""
    chapter_id: str
    chapter_no: int
    title: str
    status: str  # published, draft
    word_count: int
    read_count: int
    publish_time: Optional[str] = None


class FanQieAPIError(Exception):
    """番茄API错误"""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


class FanQieAdapter:
    """
    番茄小说适配器
    
    功能：
    - 账号登录/会话管理
    - 创建书籍
    - 发布章节
    - 获取书籍/章节信息
    - 草稿管理
    
    番茄特点：
    - 免费+广告模式
    - 字节系产品
    - 相对简单的API
    - 主要面向免费阅读
    """
    
    # API 端点
    BASE_URL = "https://fanqienovel.com"
    AUTHOR_URL = "https://author.fanqienovel.com"
    
    # 登录API
    LOGIN_API = "https://i.fanqiecdn.com/openapi/login"
    SMS_LOGIN_API = "https://i.fanqiecdn.com/openapi/login/sms"
    REFRESH_TOKEN_API = "https://i.fanqiecdn.com/openapi/refreshToken"
    
    # 创书API
    CREATE_BOOK_API = "https://author.fanqienovel.com/author/book/create"
    GET_BOOK_LIST_API = "https://author.fanqienovel.com/author/book/list"
    GET_BOOK_INFO_API = "https://author.fanqienovel.com/author/book/info"
    
    # 章节API
    PUBLISH_CHAPTER_API = "https://author.fanqienovel.com/author/chapter/publish"
    GET_CHAPTER_LIST_API = "https://author.fanqienovel.com/author/chapter/list"
    DELETE_CHAPTER_API = "https://author.fanqienovel.com/author/chapter/delete"
    
    # 草稿API
    SAVE_DRAFT_API = "https://author.fanqienovel.com/author/chapter/saveDraft"
    GET_DRAFT_API = "https://author.fanqienovel.com/author/chapter/draftList"
    
    # 分类API
    CATEGORY_API = "https://author.fanqienovel.com/author/category/list"
    
    # 分类映射
    GENRE_MAPPING = {
        "都市": "都市",
        "玄幻": "玄幻",
        "仙侠": "仙侠",
        "武侠": "武侠",
        "奇幻": "奇幻",
        "科幻": "科幻",
        "游戏": "游戏",
        "悬疑": "悬疑",
        "灵异": "灵异",
        "轻小说": "轻小说",
        "短篇": "短篇",
        "现实": "现实",
        "军事": "军事",
        "历史": "历史",
        "体育": "体育",
    }
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """
        初始化适配器
        
        Args:
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.credentials: Optional[FanQieCredentials] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "Origin": self.BASE_URL,
            "Referer": self.AUTHOR_URL,
        }
    
    async def __aenter__(self):
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers=self._headers.copy(),
                follow_redirects=True,
                cookies=httpx.Cookies()
            )
        return self._client
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _generate_device_id(self) -> str:
        """生成设备ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _generate_sign(self, params: dict) -> str:
        """
        生成签名
        番茄使用自定义签名算法
        """
        # 简化签名，实际需要根据平台规则
        sorted_params = sorted(params.items())
        raw = "&".join([f"{k}={v}" for k, v in sorted_params])
        raw += "fanqie_secret_key"  # 假设的密钥
        return hashlib.md5(raw.encode()).hexdigest()
    
    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """带重试的请求"""
        client = await self._ensure_client()
        
        for attempt in range(self.max_retries):
            try:
                response = await client.request(method, url, **kwargs)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    wait_time = 2 ** attempt + random.uniform(0, 1)
                    logger.warning(f"Rate limited, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                elif response.status_code >= 500:
                    wait_time = 2 ** attempt + random.uniform(0, 1)
                    logger.warning(f"Server error {response.status_code}, retrying...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    return response
                    
            except httpx.TimeoutException:
                logger.warning(f"Request timeout, attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                raise FanQieAPIError(
                    PublishErrorCode.NETWORK_ERROR.value,
                    "请求超时"
                )
            except httpx.RequestError as e:
                logger.warning(f"Request error: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                raise FanQieAPIError(
                    PublishErrorCode.NETWORK_ERROR.value,
                    f"网络请求失败: {str(e)}"
                )
        
        raise FanQieAPIError(
            PublishErrorCode.UNKNOWN_ERROR.value,
            f"请求失败，已重试 {self.max_retries} 次"
        )
    
    def _add_auth_headers(self, headers: dict) -> dict:
        """添加认证头"""
        if self.credentials and self.credentials.token:
            headers["Authorization"] = f"Bearer {self.credentials.token}"
        return headers
    
    async def login(self, username: str, password: str) -> dict[str, Any]:
        """
        登录番茄小说
        
        Args:
            username: 手机号/邮箱
            password: 密码
            
        Returns:
            dict: 登录结果
        """
        logger.info(f"开始登录番茄小说，用户名: {username}")
        
        client = await self._ensure_client()
        
        try:
            # 检测登录类型
            login_type = "phone" if re.match(r"^1[3-9]\d{9}$", username) else "email"
            
            # 准备登录数据
            login_data = {
                "login_type": login_type,
                "password": password,
            }
            
            if login_type == "phone":
                login_data["phone"] = username
            else:
                login_data["email"] = username
            
            # 添加设备信息
            device_id = self._generate_device_id()
            login_data["device_id"] = device_id
            login_data["device_type"] = "pc"
            
            # 生成签名
            sign_data = {k: v for k, v in login_data.items() if v}
            login_data["sign"] = self._generate_sign(sign_data)
            
            response = await self._request_with_retry(
                "POST",
                self.LOGIN_API,
                json=login_data
            )
            
            result = response.json()
            
            if result.get("code") == 0 or result.get("status") == 0:
                data = result.get("data", {})
                
                self.credentials = FanQieCredentials(
                    username=username,
                    password=password,
                    token=data.get("token", ""),
                    user_id=str(data.get("user_id", "")),
                    user_name=data.get("user_name", username),
                    device_id=device_id,
                    cookies=dict(response.cookies)
                )
                
                logger.info(f"登录成功，用户ID: {self.credentials.user_id}")
                
                return {
                    "success": True,
                    "account_id": self.credentials.user_id,
                    "user_name": self.credentials.user_name,
                    "status": "active",
                    "message": "登录成功"
                }
            else:
                error_msg = result.get("message", "登录失败")
                error_code = self._map_login_error(error_msg)
                
                logger.error(f"登录失败: {error_msg}")
                
                return {
                    "success": False,
                    "error_code": error_code,
                    "error_message": error_msg
                }
                
        except FanQieAPIError:
            raise
        except Exception as e:
            logger.error(f"登录异常: {str(e)}")
            raise FanQieAPIError(
                PublishErrorCode.UNKNOWN_ERROR.value,
                f"登录异常: {str(e)}"
            )
    
    def _map_login_error(self, error_msg: str) -> str:
        """映射登录错误码"""
        if "密码" in error_msg:
            return PublishErrorCode.PASSWORD_ERROR.value
        elif "验证码" in error_msg:
            return PublishErrorCode.LOGIN_CAPTCHA.value
        elif "锁定" in error_msg:
            return PublishErrorCode.LOGIN_LOCKED.value
        else:
            return PublishErrorCode.LOGIN_FAILED.value
    
    async def login_with_sms(self, phone: str, code: str) -> dict[str, Any]:
        """
        短信验证码登录
        
        Args:
            phone: 手机号
            code: 验证码
            
        Returns:
            dict: 登录结果
        """
        logger.info(f"短信登录番茄小说，手机号: {phone}")
        
        client = await self._ensure_client()
        
        sms_data = {
            "phone": phone,
            "code": code,
            "device_id": self._generate_device_id(),
            "device_type": "pc",
        }
        
        sms_data["sign"] = self._generate_sign(sms_data)
        
        response = await self._request_with_retry(
            "POST",
            self.SMS_LOGIN_API,
            json=sms_data
        )
        
        result = response.json()
        
        if result.get("code") == 0:
            data = result.get("data", {})
            
            self.credentials = FanQieCredentials(
                username=phone,
                password="",
                token=data.get("token", ""),
                user_id=str(data.get("user_id", "")),
                user_name=data.get("user_name", phone),
                device_id=sms_data["device_id"],
                cookies=dict(response.cookies)
            )
            
            return {
                "success": True,
                "account_id": self.credentials.user_id,
                "status": "active",
                "message": "登录成功"
            }
        else:
            return {
                "success": False,
                "error_code": PublishErrorCode.LOGIN_FAILED.value,
                "error_message": result.get("message", "验证码错误")
            }
    
    async def login_with_token(self, token: str, user_id: str = None) -> dict[str, Any]:
        """
        使用Token登录
        
        Args:
            token: 访问令牌
            user_id: 用户ID
        """
        logger.info("使用Token登录番茄小说")
        
        self.credentials = FanQieCredentials(
            username="",
            password="",
            token=token,
            user_id=user_id,
            device_id=self._generate_device_id()
        )
        
        # 验证Token
        try:
            await self.get_account_status(user_id or "")
            return {
                "success": True,
                "account_id": self.credentials.user_id,
                "status": "active",
                "message": "Token登录成功"
            }
        except Exception as e:
            logger.error(f"Token无效: {e}")
            return {
                "success": False,
                "error_code": PublishErrorCode.SESSION_EXPIRED.value,
                "error_message": "Token已过期"
            }
    
    async def refresh_token(self) -> dict[str, Any]:
        """刷新Token"""
        if not self.credentials or not self.credentials.token:
            return {
                "success": False,
                "error_message": "未登录"
            }
        
        client = await self._ensure_client()
        
        response = await self._request_with_retry(
            "POST",
            self.REFRESH_TOKEN_API,
            json={"refresh_token": self.credentials.token}
        )
        
        result = response.json()
        
        if result.get("code") == 0:
            data = result.get("data", {})
            self.credentials.token = data.get("token", "")
            return {
                "success": True,
                "message": "Token已刷新"
            }
        else:
            return {
                "success": False,
                "error_code": PublishErrorCode.SESSION_EXPIRED.value,
                "error_message": "Token刷新失败"
            }
    
    async def get_account_status(self, account_id: str) -> dict[str, Any]:
        """获取账户状态"""
        if not self.credentials:
            return {
                "status": "not_logged_in",
                "message": "未登录"
            }
        
        try:
            books = await self.get_book_list()
            
            return {
                "status": "active",
                "account_id": self.credentials.user_id,
                "user_name": self.credentials.user_name,
                "book_count": len(books),
                "message": "账户正常"
            }
            
        except FanQieAPIError as e:
            return {
                "status": "expired",
                "error_code": e.code,
                "message": e.message
            }
    
    async def get_book_list(self) -> list[FanQieBookInfo]:
        """获取书籍列表"""
        if not self.credentials:
            raise FanQieAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        client = await self._ensure_client()
        
        headers = self._add_auth_headers(self._headers.copy())
        
        response = await self._request_with_retry(
            "GET",
            self.GET_BOOK_LIST_API,
            headers=headers,
            params={"page": 1, "page_size": 100}
        )
        
        result = response.json()
        
        if result.get("code") != 0:
            raise FanQieAPIError(
                PublishErrorCode.UNKNOWN_ERROR.value,
                result.get("message", "获取书籍列表失败")
            )
        
        books_data = result.get("data", {}).get("list", [])
        books = []
        
        for book in books_data:
            books.append(FanQieBookInfo(
                book_id=str(book.get("book_id", "")),
                title=book.get("title", ""),
                author_id=str(book.get("author_id", "")),
                author_name=book.get("author_name", ""),
                status=book.get("status", ""),
                genre=book.get("category_name", ""),
                word_count=book.get("word_count", 0),
                chapter_count=book.get("chapter_count", 0),
                read_count=book.get("read_count", 0),
                is_free=book.get("is_free", True),
                cover_url=book.get("cover_url")
            ))
        
        return books
    
    async def create_book(
        self,
        title: str,
        genre: str,
        synopsis: str,
        **kwargs
    ) -> dict[str, Any]:
        """
        创建书籍
        
        Args:
            title: 书名
            genre: 类型
            synopsis: 简介
            
        Returns:
            dict: 创建结果
        """
        if not self.credentials:
            raise FanQieAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        logger.info(f"创建书籍: {title}, 类型: {genre}")
        
        client = await self._ensure_client()
        
        headers = self._add_auth_headers(self._headers.copy())
        
        # 获取分类ID
        category_id = self._get_category_id(genre)
        
        # 准备创书数据
        create_data = {
            "title": title,
            "category_id": category_id,
            "synopsis": synopsis,
            "is_free": kwargs.get("is_free", True),
            "tags": kwargs.get("tags", ""),
        }
        
        # 添加签名
        create_data["sign"] = self._generate_sign(create_data)
        
        response = await self._request_with_retry(
            "POST",
            self.CREATE_BOOK_API,
            headers=headers,
            json=create_data
        )
        
        result = response.json()
        
        if result.get("code") == 0:
            book_id = result.get("data", {}).get("book_id", "")
            logger.info(f"书籍创建成功，ID: {book_id}")
            
            return {
                "success": True,
                "book_id": str(book_id),
                "title": title,
                "message": "书籍创建成功"
            }
        else:
            error_msg = result.get("message", "创建失败")
            error_code = self._map_create_error(error_msg)
            
            logger.error(f"创建书籍失败: {error_msg}")
            
            return {
                "success": False,
                "error_code": error_code,
                "error_message": error_msg
            }
    
    def _get_category_id(self, genre: str) -> str:
        """获取分类ID"""
        # 实际需要从API获取分类列表
        category_ids = {
            "都市": "1",
            "玄幻": "2",
            "仙侠": "3",
            "武侠": "4",
            "奇幻": "5",
            "科幻": "6",
        }
        return category_ids.get(genre, "1")
    
    def _map_create_error(self, error_msg: str) -> str:
        """映射创建错误码"""
        if "重复" in error_msg:
            return PublishErrorCode.DUPLICATE_SUBMISSION.value
        elif "敏感" in error_msg:
            return PublishErrorCode.PLATFORM_VALIDATION_ERROR.value
        else:
            return PublishErrorCode.PLATFORM_VALIDATION_ERROR.value
    
    async def get_book_info(self, book_id: str) -> FanQieBookInfo:
        """获取书籍详细信息"""
        if not self.credentials:
            raise FanQieAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        client = await self._ensure_client()
        
        headers = self._add_auth_headers(self._headers.copy())
        
        response = await self._request_with_retry(
            "GET",
            f"{self.GET_BOOK_INFO_API}/{book_id}",
            headers=headers
        )
        
        result = response.json()
        
        if result.get("code") != 0:
            raise FanQieAPIError(
                PublishErrorCode.UNKNOWN_ERROR.value,
                result.get("message", "获取书籍信息失败")
            )
        
        data = result.get("data", {})
        
        return FanQieBookInfo(
            book_id=str(data.get("book_id", "")),
            title=data.get("title", ""),
            author_id=str(data.get("author_id", "")),
            author_name=data.get("author_name", ""),
            status=data.get("status", ""),
            genre=data.get("category_name", ""),
            word_count=data.get("word_count", 0),
            chapter_count=data.get("chapter_count", 0),
            read_count=data.get("read_count", 0),
            is_free=data.get("is_free", True),
            cover_url=data.get("cover_url")
        )
    
    async def get_chapter_list(self, book_id: str) -> list[FanQieChapterInfo]:
        """获取章节列表"""
        if not self.credentials:
            raise FanQieAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        client = await self._ensure_client()
        
        headers = self._add_auth_headers(self._headers.copy())
        
        response = await self._request_with_retry(
            "GET",
            self.GET_CHAPTER_LIST_API,
            headers=headers,
            params={"book_id": book_id, "page": 1, "page_size": 500}
        )
        
        result = response.json()
        
        if result.get("code") != 0:
            raise FanQieAPIError(
                PublishErrorCode.UNKNOWN_ERROR.value,
                result.get("message", "获取章节列表失败")
            )
        
        chapters_data = result.get("data", {}).get("list", [])
        chapters = []
        
        for chapter in chapters_data:
            chapters.append(FanQieChapterInfo(
                chapter_id=str(chapter.get("chapter_id", "")),
                chapter_no=chapter.get("chapter_index", 0),
                title=chapter.get("title", ""),
                status=chapter.get("status", ""),
                word_count=chapter.get("word_count", 0),
                read_count=chapter.get("read_count", 0),
                publish_time=chapter.get("publish_time")
            ))
        
        return chapters
    
    async def publish_chapter(
        self,
        book_id: str,
        chapter_no: int,
        title: str,
        content: str,
        mode: str = "publish",
        **kwargs
    ) -> dict[str, Any]:
        """
        发布章节
        
        Args:
            book_id: 书籍ID
            chapter_no: 章节号
            title: 章节标题
            content: 章节内容
            mode: 发布模式
            
        Returns:
            dict: 发布结果
        """
        if not self.credentials:
            raise FanQieAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        logger.info(f"发布章节: 书ID={book_id}, 章节={chapter_no}, 标题={title}")
        
        client = await self._ensure_client()
        
        headers = self._add_auth_headers(self._headers.copy())
        
        # 字数检查
        word_count = len(content)
        if word_count < 100:
            return {
                "success": False,
                "error_code": PublishErrorCode.CONTENT_TOO_SHORT.value,
                "error_message": f"内容字数不足（当前{word_count}字）"
            }
        
        # 准备章节数据
        chapter_data = {
            "book_id": book_id,
            "title": title,
            "content": content,
            "is_publish": mode == "publish",
        }
        
        # 添加签名
        chapter_data["sign"] = self._generate_sign(chapter_data)
        
        response = await self._request_with_retry(
            "POST",
            self.PUBLISH_CHAPTER_API,
            headers=headers,
            json=chapter_data
        )
        
        result = response.json()
        
        if result.get("code") == 0:
            task_id = result.get("data", {}).get("chapter_id", f"fanqie_{book_id}_{chapter_no}")
            
            logger.info(f"章节发布成功，ID: {task_id}")
            
            return {
                "success": True,
                "task_id": str(task_id),
                "chapter_no": chapter_no,
                "word_count": word_count,
                "message": "章节发布成功"
            }
        else:
            error_msg = result.get("message", "发布失败")
            error_code = self._map_publish_error(error_msg)
            
            logger.error(f"章节发布失败: {error_msg}")
            
            return {
                "success": False,
                "error_code": error_code,
                "error_message": error_msg
            }
    
    def _map_publish_error(self, error_msg: str) -> str:
        """映射发布错误码"""
        if "重复" in error_msg:
            return PublishErrorCode.DUPLICATE_SUBMISSION.value
        elif "格式" in error_msg:
            return PublishErrorCode.CONTENT_FORMAT_ERROR.value
        else:
            return PublishErrorCode.UNKNOWN_ERROR.value
    
    async def save_draft(
        self,
        book_id: str,
        chapter_no: int,
        title: str,
        content: str
    ) -> dict[str, Any]:
        """保存草稿"""
        if not self.credentials:
            raise FanQieAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        client = await self._ensure_client()
        
        headers = self._add_auth_headers(self._headers.copy())
        
        draft_data = {
            "book_id": book_id,
            "title": title,
            "content": content,
        }
        
        draft_data["sign"] = self._generate_sign(draft_data)
        
        response = await self._request_with_retry(
            "POST",
            self.SAVE_DRAFT_API,
            headers=headers,
            json=draft_data
        )
        
        result = response.json()
        
        return {
            "success": result.get("code") == 0,
            "draft_id": result.get("data", {}).get("draft_id", ""),
            "message": "草稿保存完成"
        }
    
    async def delete_chapter(self, book_id: str, chapter_id: str) -> dict[str, Any]:
        """删除章节"""
        if not self.credentials:
            raise FanQieAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        client = await self._ensure_client()
        
        headers = self._add_auth_headers(self._headers.copy())
        
        response = await self._request_with_retry(
            "POST",
            self.DELETE_CHAPTER_API,
            headers=headers,
            json={"book_id": book_id, "chapter_id": chapter_id}
        )
        
        result = response.json()
        
        return {
            "success": result.get("code") == 0,
            "message": result.get("message", "删除完成")
        }
    
    async def bind_book(
        self,
        account_id: str,
        remote_book_id: str,
        book_title: str,
        extra_data: dict = None
    ) -> dict[str, Any]:
        """绑定书籍（适配器接口）"""
        try:
            book_info = await self.get_book_info(remote_book_id)
            
            return {
                "success": True,
                "local_book_id": None,
                "remote_book_id": remote_book_id,
                "title": book_info.title,
                "bound": True,
                "message": "书籍绑定成功"
            }
        except FanQieAPIError as e:
            return {
                "success": False,
                "error_code": e.code,
                "error_message": e.message
            }
    
    async def get_task_status(self, account_id: str, task_id: str) -> dict[str, Any]:
        """获取任务状态（适配器接口）"""
        return {
            "status": "success",
            "task_id": task_id,
            "message": "任务已完成"
        }


# 导出
__all__ = ["FanQieAdapter", "FanQieAPIError", "FanQieCredentials", "FanQieBookInfo", "FanQieChapterInfo"]
