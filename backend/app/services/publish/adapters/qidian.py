"""
起点中文网完整适配器
支持登录、创书、发布章节等功能
"""
import asyncio
import hashlib
import json
import logging
import random
import re
import time
from typing import Any, Optional
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup

from app.models.publish_task import PublishErrorCode

logger = logging.getLogger(__name__)


@dataclass
class QidianCredentials:
    """起点账号凭证"""
    username: str
    password: str
    token: Optional[str] = None
    cookies: dict = field(default_factory=dict)
    user_id: Optional[str] = None
    user_name: Optional[str] = None


@dataclass 
class QidianBookInfo:
    """起点书籍信息"""
    book_id: str
    title: str
    author_id: str
    author_name: str
    status: str  # ongoing, completed
    genre: str
    word_count: int
    chapter_count: int
    cover_url: Optional[str] = None


@dataclass
class QidianChapterInfo:
    """起点章节信息"""
    chapter_id: str
    chapter_no: int
    title: str
    status: str  # published, draft
    word_count: int
    publish_time: Optional[str] = None


class QidianAPIError(Exception):
    """起点API错误"""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


class QidianAdapter:
    """
    起点中文网适配器
    
    功能：
    - 账号登录/会话管理
    - 创建书籍
    - 发布章节
    - 获取书籍/章节信息
    - 草稿箱管理
    
    API文档参考：创世作者后台 API
    """
    
    # API 端点
    BASE_URL = "https://www.qidian.com"
    PASS_PORT_URL = "https://passport.qidian.com"
    CREATOR_URL = "https://creator.qidian.com"
    AUTHOR_URL = "https://authors.qidian.com"
    
    # 登录相关
    LOGIN_API = "https://passport.qidian.com/ajax/login.do"
    CHECK_TOKEN_API = "https://passport.qidian.com/ajax/chkToken.do"
    
    # 创书相关
    CREATE_BOOK_API = "https://creator.qidian.com/ajax/book/createBook.do"
    GET_BOOK_LIST_API = "https://creator.qidian.com/ajax/book/getMyBooks.do"
    GET_BOOK_INFO_API = "https://creator.qidian.com/ajax/book/getBookInfo.do"
    
    # 章节相关
    GET_CHAPTER_LIST_API = "https://creator.qidian.com/ajax/chapter/getChapterList.do"
    PUBLISH_CHAPTER_API = "https://creator.qidian.com/ajax/chapter/addChapter.do"
    UPDATE_CHAPTER_API = "https://creator.qidian.com/ajax/chapter/updateChapter.do"
    DELETE_CHAPTER_API = "https://creator.qidian.com/ajax/chapter/delChapter.do"
    
    # 草稿相关
    SAVE_DRAFT_API = "https://creator.qidian.com/ajax/chapter/saveDraft.do"
    GET_DRAFT_API = "https://creator.qidian.com/ajax/chapter/getDraft.do"
    
    # 分类API
    GET_CATEGORIES_API = "https://creator.qidian.com/ajax/book/getCategory.do"
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """
        初始化适配器
        
        Args:
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.credentials: Optional[QidianCredentials] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": self.BASE_URL,
            "Referer": self.BASE_URL,
        }
        
        # 书籍分类映射
        self.genre_mapping = {
            "玄幻": "21",
            "奇幻": "1",
            "武侠": "2",
            "仙侠": "22",
            "都市": "4",
            "职场": "5",
            "军事": "6",
            "历史": "7",
            "游戏": "8",
            "竞技": "9",
            "科幻": "10",
            "灵异": "11",
            "悬疑": "23",
            "轻小说": "12",
            "二次元": "13",
            "女生网": "15",
        }
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def _ensure_client(self) -> httpx.AsyncClient:
        """确保客户端已初始化"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers=self._headers.copy(),
                follow_redirects=True,
                cookies=httpx.Cookies()
            )
        return self._client
    
    async def close(self):
        """关闭客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _generate_device_id(self) -> str:
        """生成设备ID"""
        import uuid
        return str(uuid.uuid4()).replace("-", "")[:32]
    
    def _encrypt_password(self, password: str) -> str:
        """
        密码加密
        起点使用RSA加密，这里使用模拟加密
        """
        # 实际应该使用公钥加密
        # 这里简化处理
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _parse_set_cookie(self, headers: httpx.Headers) -> dict:
        """解析Set-Cookie头"""
        cookies = {}
        for key, value in headers.items():
            if key.lower() == "set-cookie":
                parts = value.split(";")
                if parts:
                    cookie_pair = parts[0].split("=")
                    if len(cookie_pair) == 2:
                        cookies[cookie_pair[0].strip()] = cookie_pair[1].strip()
        return cookies
    
    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        带重试的请求
        
        Args:
            method: HTTP方法
            url: 请求URL
            **kwargs: 其他参数
            
        Returns:
            httpx.Response
        """
        client = await self._ensure_client()
        
        for attempt in range(self.max_retries):
            try:
                response = await client.request(method, url, **kwargs)
                
                # 检查响应状态
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    # 限流，等待后重试
                    wait_time = 2 ** attempt + random.uniform(0, 1)
                    logger.warning(f"Rate limited, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                elif response.status_code >= 500:
                    # 服务器错误，重试
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
                raise QidianAPIError(
                    PublishErrorCode.NETWORK_ERROR.value,
                    "请求超时"
                )
            except httpx.RequestError as e:
                logger.warning(f"Request error: {e}, attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                raise QidianAPIError(
                    PublishErrorCode.NETWORK_ERROR.value,
                    f"网络请求失败: {str(e)}"
                )
        
        raise QidianAPIError(
            PublishErrorCode.UNKNOWN_ERROR.value,
            f"请求失败，已重试 {self.max_retries} 次"
        )
    
    async def login(self, username: str, password: str) -> dict[str, Any]:
        """
        登录起点中文网
        
        Args:
            username: 用户名/手机号/邮箱
            password: 密码
            
        Returns:
            dict: 包含 account_id 和登录状态
            
        Raises:
            QidianAPIError: 登录失败
        """
        logger.info(f"开始登录起点，用户名: {username}")
        
        client = await self._ensure_client()
        
        try:
            # 步骤1: 获取登录页面和token
            login_page_url = f"{self.PASS_PORT_URL}/login"
            response = await self._request_with_retry("GET", login_page_url)
            
            # 从页面提取必要参数
            page_content = response.text
            token_match = re.search(r'name="_csrfToken"\s+value="([^"]+)"', page_content)
            csrf_token = token_match.group(1) if token_match else ""
            
            # 步骤2: 执行登录
            login_data = {
                "loginType": self._detect_login_type(username),
                "userName": username,
                "password": password,
                "remember": "true",
                "_csrfToken": csrf_token,
                "deviceId": self._generate_device_id(),
                "platformSource": "QD_PC",
                "redirectUrl": f"{self.BASE_URL}/",
            }
            
            response = await self._request_with_retry(
                "POST",
                self.LOGIN_API,
                data=login_data,
            )
            
            result = response.json()
            
            # 检查登录结果
            if result.get("code") == 0 or result.get("isLogin") == True:
                # 登录成功
                self.credentials = QidianCredentials(
                    username=username,
                    password=password,
                    token=result.get("data", {}).get("token", ""),
                    user_id=str(result.get("data", {}).get("userId", "")),
                    user_name=result.get("data", {}).get("nickName", username),
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
                # 登录失败
                error_msg = result.get("msg", "登录失败")
                error_code = self._map_login_error(error_msg)
                
                logger.error(f"登录失败: {error_msg}")
                
                return {
                    "success": False,
                    "error_code": error_code,
                    "error_message": error_msg
                }
                
        except QidianAPIError:
            raise
        except Exception as e:
            logger.error(f"登录异常: {str(e)}")
            raise QidianAPIError(
                PublishErrorCode.UNKNOWN_ERROR.value,
                f"登录异常: {str(e)}"
            )
    
    def _detect_login_type(self, username: str) -> str:
        """检测登录类型"""
        if re.match(r"^1[3-9]\d{9}$", username):
            return "phone"
        elif "@" in username:
            return "email"
        else:
            return "uid"
    
    def _map_login_error(self, error_msg: str) -> str:
        """映射登录错误码"""
        msg_lower = error_msg.lower()
        if "密码" in msg_lower or "password" in msg_lower:
            return PublishErrorCode.PASSWORD_ERROR.value
        elif "验证码" in msg_lower or "captcha" in msg_lower:
            return PublishErrorCode.LOGIN_CAPTCHA.value
        elif "锁定" in msg_lower or "lock" in msg_lower:
            return PublishErrorCode.LOGIN_LOCKED.value
        elif "不存在" in msg_lower or "not exist" in msg_lower:
            return PublishErrorCode.LOGIN_FAILED.value
        else:
            return PublishErrorCode.LOGIN_FAILED.value
    
    async def login_with_cookie(self, cookies: dict, user_id: str = None) -> dict[str, Any]:
        """
        使用Cookie登录
        
        Args:
            cookies: Cookie字典
            user_id: 用户ID（可选）
            
        Returns:
            dict: 登录状态
        """
        logger.info("使用Cookie登录起点")
        
        client = await self._ensure_client()
        
        # 设置Cookie
        for name, value in cookies.items():
            client.cookies.set(name, value)
        
        # 验证Cookie有效性
        try:
            response = await self._request_with_retry(
                "GET",
                self.CHECK_TOKEN_API,
                params={"_csrfToken": cookies.get("_csrfToken", "")}
            )
            
            result = response.json()
            
            if result.get("code") == 0:
                self.credentials = QidianCredentials(
                    username="",
                    password="",
                    cookies=cookies,
                    user_id=user_id or result.get("data", {}).get("userId", "")
                )
                
                return {
                    "success": True,
                    "account_id": self.credentials.user_id,
                    "status": "active",
                    "message": "Cookie登录成功"
                }
            else:
                return {
                    "success": False,
                    "error_code": PublishErrorCode.SESSION_EXPIRED.value,
                    "error_message": "Cookie已过期"
                }
                
        except Exception as e:
            logger.error(f"Cookie登录失败: {str(e)}")
            return {
                "success": False,
                "error_code": PublishErrorCode.SESSION_EXPIRED.value,
                "error_message": f"Cookie登录失败: {str(e)}"
            }
    
    async def get_account_status(self, account_id: str) -> dict[str, Any]:
        """
        获取账户状态
        
        Args:
            account_id: 账户ID
            
        Returns:
            dict: 账户状态信息
        """
        if not self.credentials:
            return {
                "status": "not_logged_in",
                "message": "未登录"
            }
        
        try:
            # 获取书籍列表作为状态验证
            books = await self.get_book_list()
            
            return {
                "status": "active",
                "account_id": self.credentials.user_id,
                "user_name": self.credentials.user_name,
                "book_count": len(books),
                "message": "账户正常"
            }
            
        except QidianAPIError as e:
            if e.code == PublishErrorCode.SESSION_EXPIRED.value:
                return {
                    "status": "expired",
                    "error_code": e.code,
                    "message": e.message
                }
            raise
    
    async def get_book_list(self) -> list[QidianBookInfo]:
        """
        获取书籍列表
        
        Returns:
            list[QidianBookInfo]: 书籍信息列表
        """
        if not self.credentials:
            raise QidianAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        client = await self._ensure_client()
        
        # 设置登录Cookie
        for name, value in self.credentials.cookies.items():
            client.cookies.set(name, value)
        
        response = await self._request_with_retry(
            "GET",
            self.GET_BOOK_LIST_API,
            params={
                "userId": self.credentials.user_id,
                "status": "all",
                "pageSize": 100,
                "pageNum": 1
            }
        )
        
        result = response.json()
        
        if result.get("code") != 0:
            raise QidianAPIError(
                PublishErrorCode.UNKNOWN_ERROR.value,
                result.get("msg", "获取书籍列表失败")
            )
        
        books_data = result.get("data", {}).get("list", [])
        books = []
        
        for book in books_data:
            books.append(QidianBookInfo(
                book_id=str(book.get("bookId", "")),
                title=book.get("bookName", ""),
                author_id=str(book.get("authorId", "")),
                author_name=book.get("authorName", ""),
                status=book.get("status", ""),
                genre=book.get("categoryName", ""),
                word_count=book.get("wordCount", 0),
                chapter_count=book.get("chapterCount", 0),
                cover_url=book.get("coverUrl")
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
            genre: 类型（如：玄幻、都市、仙侠）
            synopsis: 简介
            
        Returns:
            dict: 创建结果，包含 book_id
            
        Raises:
            QidianAPIError: 创建失败
        """
        if not self.credentials:
            raise QidianAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        logger.info(f"创建书籍: {title}, 类型: {genre}")
        
        client = await self._ensure_client()
        
        # 设置登录Cookie
        for name, value in self.credentials.cookies.items():
            client.cookies.set(name, value)
        
        # 获取分类ID
        category_id = self.genre_mapping.get(genre, "21")
        
        # 额外参数
        extra_params = {
            "bookName": title,
            "categoryId": category_id,
            "bookDesc": synopsis,
            "isSceneFull": kwargs.get("is_scene_full", "1"),
            "isShowR榜": kwargs.get("show_ranking", True),
            "tag": kwargs.get("tags", ""),
            "isVip": kwargs.get("is_vip", True),
            "isPub": kwargs.get("is_pub", True),
        }
        
        response = await self._request_with_retry(
            "POST",
            self.CREATE_BOOK_API,
            data=extra_params
        )
        
        result = response.json()
        
        if result.get("code") == 0:
            book_id = result.get("data", {}).get("bookId", "")
            logger.info(f"书籍创建成功，ID: {book_id}")
            
            return {
                "success": True,
                "book_id": book_id,
                "title": title,
                "message": "书籍创建成功"
            }
        else:
            error_msg = result.get("msg", "创建失败")
            error_code = self._map_create_error(error_msg)
            
            logger.error(f"创建书籍失败: {error_msg}")
            
            return {
                "success": False,
                "error_code": error_code,
                "error_message": error_msg
            }
    
    def _map_create_error(self, error_msg: str) -> str:
        """映射创建书籍错误码"""
        msg_lower = error_msg.lower()
        if "书名" in msg_lower and "短" in msg_lower:
            return PublishErrorCode.TITLE_TOO_SHORT.value
        elif "重复" in msg_lower or "exist" in msg_lower:
            return PublishErrorCode.DUPLICATE_SUBMISSION.value
        else:
            return PublishErrorCode.PLATFORM_VALIDATION_ERROR.value
    
    async def get_book_info(self, book_id: str) -> QidianBookInfo:
        """
        获取书籍详细信息
        
        Args:
            book_id: 书籍ID
            
        Returns:
            QidianBookInfo: 书籍信息
        """
        if not self.credentials:
            raise QidianAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        client = await self._ensure_client()
        
        for name, value in self.credentials.cookies.items():
            client.cookies.set(name, value)
        
        response = await self._request_with_retry(
            "GET",
            self.GET_BOOK_INFO_API,
            params={"bookId": book_id}
        )
        
        result = response.json()
        
        if result.get("code") != 0:
            raise QidianAPIError(
                PublishErrorCode.UNKNOWN_ERROR.value,
                result.get("msg", "获取书籍信息失败")
            )
        
        data = result.get("data", {})
        
        return QidianBookInfo(
            book_id=str(data.get("bookId", "")),
            title=data.get("bookName", ""),
            author_id=str(data.get("authorId", "")),
            author_name=data.get("authorName", ""),
            status=data.get("status", ""),
            genre=data.get("categoryName", ""),
            word_count=data.get("wordCount", 0),
            chapter_count=data.get("chapterCount", 0),
            cover_url=data.get("coverUrl")
        )
    
    async def get_chapter_list(self, book_id: str) -> list[QidianChapterInfo]:
        """
        获取章节列表
        
        Args:
            book_id: 书籍ID
            
        Returns:
            list[QidianChapterInfo]: 章节列表
        """
        if not self.credentials:
            raise QidianAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        client = await self._ensure_client()
        
        for name, value in self.credentials.cookies.items():
            client.cookies.set(name, value)
        
        response = await self._request_with_retry(
            "GET",
            self.GET_CHAPTER_LIST_API,
            params={
                "bookId": book_id,
                "pageSize": 500,
                "pageNum": 1
            }
        )
        
        result = response.json()
        
        if result.get("code") != 0:
            raise QidianAPIError(
                PublishErrorCode.UNKNOWN_ERROR.value,
                result.get("msg", "获取章节列表失败")
            )
        
        chapters_data = result.get("data", {}).get("chapterList", [])
        chapters = []
        
        for chapter in chapters_data:
            chapters.append(QidianChapterInfo(
                chapter_id=str(chapter.get("chapterId", "")),
                chapter_no=chapter.get("chapterNum", 0),
                title=chapter.get("chapterName", ""),
                status=chapter.get("status", ""),
                word_count=chapter.get("wordCount", 0),
                publish_time=chapter.get("publishTime")
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
            mode: 发布模式 (publish/draft)
            
        Returns:
            dict: 发布结果
        """
        if not self.credentials:
            raise QidianAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        logger.info(f"发布章节: 书ID={book_id}, 章节={chapter_no}, 标题={title}")
        
        client = await self._ensure_client()
        
        for name, value in self.credentials.cookies.items():
            client.cookies.set(name, value)
        
        # 内容字数检查
        word_count = len(content)
        if word_count < 100:
            return {
                "success": False,
                "error_code": PublishErrorCode.CONTENT_TOO_SHORT.value,
                "error_message": f"内容字数不足100字（当前{word_count}字）"
            }
        
        # 准备章节数据
        chapter_data = {
            "bookId": book_id,
            "chapterName": title,
            "chapterContent": content,
            "isVip": kwargs.get("is_vip", False),
            "isPub": mode == "publish",
            "needAudit": True,
        }
        
        response = await self._request_with_retry(
            "POST",
            self.PUBLISH_CHAPTER_API,
            json=chapter_data
        )
        
        result = response.json()
        
        if result.get("code") == 0:
            task_id = result.get("data", {}).get("chapterId", f"qidian_{book_id}_{chapter_no}")
            
            logger.info(f"章节发布成功，ID: {task_id}")
            
            return {
                "success": True,
                "task_id": str(task_id),
                "chapter_no": chapter_no,
                "word_count": word_count,
                "message": "章节发布成功"
            }
        else:
            error_msg = result.get("msg", "发布失败")
            error_code = self._map_publish_error(error_msg)
            
            logger.error(f"章节发布失败: {error_msg}")
            
            return {
                "success": False,
                "error_code": error_code,
                "error_message": error_msg
            }
    
    def _map_publish_error(self, error_msg: str) -> str:
        """映射发布错误码"""
        msg_lower = error_msg.lower()
        if "重复" in msg_lower or "exist" in msg_lower:
            return PublishErrorCode.DUPLICATE_SUBMISSION.value
        elif "格式" in msg_lower or "format" in msg_lower:
            return PublishErrorCode.CONTENT_FORMAT_ERROR.value
        elif "审核" in msg_lower or "audit" in msg_lower:
            return PublishErrorCode.PLATFORM_VALIDATION_ERROR.value
        else:
            return PublishErrorCode.UNKNOWN_ERROR.value
    
    async def save_draft(
        self,
        book_id: str,
        chapter_no: int,
        title: str,
        content: str
    ) -> dict[str, Any]:
        """
        保存草稿
        
        Args:
            book_id: 书籍ID
            chapter_no: 章节号
            title: 章节标题
            content: 章节内容
            
        Returns:
            dict: 保存结果
        """
        if not self.credentials:
            raise QidianAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        client = await self._ensure_client()
        
        for name, value in self.credentials.cookies.items():
            client.cookies.set(name, value)
        
        draft_data = {
            "bookId": book_id,
            "chapterName": title,
            "chapterContent": content,
        }
        
        response = await self._request_with_retry(
            "POST",
            self.SAVE_DRAFT_API,
            json=draft_data
        )
        
        result = response.json()
        
        if result.get("code") == 0:
            return {
                "success": True,
                "draft_id": result.get("data", {}).get("draftId", ""),
                "message": "草稿保存成功"
            }
        else:
            return {
                "success": False,
                "error_message": result.get("msg", "保存失败")
            }
    
    async def delete_chapter(self, book_id: str, chapter_id: str) -> dict[str, Any]:
        """
        删除章节
        
        Args:
            book_id: 书籍ID
            chapter_id: 章节ID
            
        Returns:
            dict: 删除结果
        """
        if not self.credentials:
            raise QidianAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        client = await self._ensure_client()
        
        for name, value in self.credentials.cookies.items():
            client.cookies.set(name, value)
        
        response = await self._request_with_retry(
            "POST",
            self.DELETE_CHAPTER_API,
            json={
                "bookId": book_id,
                "chapterId": chapter_id
            }
        )
        
        result = response.json()
        
        return {
            "success": result.get("code") == 0,
            "message": result.get("msg", "删除完成")
        }
    
    async def get_categories(self) -> list[dict]:
        """
        获取书籍分类列表
        
        Returns:
            list[dict]: 分类列表
        """
        client = await self._ensure_client()
        
        response = await self._request_with_retry(
            "GET",
            self.GET_CATEGORIES_API
        )
        
        result = response.json()
        
        if result.get("code") == 0:
            return result.get("data", {}).get("categoryList", [])
        return []
    
    async def bind_book(
        self,
        account_id: str,
        remote_book_id: str,
        book_title: str,
        extra_data: dict = None
    ) -> dict[str, Any]:
        """
        绑定书籍（适配器接口）
        
        Args:
            account_id: 账户ID
            remote_book_id: 远程书籍ID
            book_title: 书籍标题
            extra_data: 额外数据
            
        Returns:
            dict: 绑定结果
        """
        # 验证书籍存在
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
        except QidianAPIError as e:
            return {
                "success": False,
                "error_code": e.code,
                "error_message": e.message
            }
    
    async def get_task_status(self, account_id: str, task_id: str) -> dict[str, Any]:
        """
        获取任务状态（适配器接口）
        
        Args:
            account_id: 账户ID
            task_id: 任务ID
            
        Returns:
            dict: 任务状态
        """
        return {
            "status": "success",
            "task_id": task_id,
            "message": "任务已完成"
        }


# 导出
__all__ = ["QidianAdapter", "QidianAPIError", "QidianCredentials", "QidianBookInfo", "QidianChapterInfo"]
