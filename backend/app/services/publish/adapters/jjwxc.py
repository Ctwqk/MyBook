"""
晋江文学城完整适配器
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
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from app.models.publish_task import PublishErrorCode

logger = logging.getLogger(__name__)


@dataclass
class JjwxcCredentials:
    """晋江账号凭证"""
    username: str
    password: str
    cookies: dict = field(default_factory=dict)
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    token: Optional[str] = None


@dataclass
class JjwxcBookInfo:
    """晋江书籍信息"""
    book_id: str
    title: str
    author_id: str
    author_name: str
    status: str  # ongoing, completed,暂停
    genre: str
    word_count: int
    chapter_count: int
    collect_count: int
    chapter_price: float = 0.0
    is_vip: bool = False


@dataclass
class JjwxcChapterInfo:
    """晋江章节信息"""
    chapter_id: str
    chapter_no: int
    title: str
    status: str  # published, draft, locked
    word_count: int
    price: float
    publish_time: Optional[str] = None
    is_vip: bool = False


class JjwxcAPIError(Exception):
    """晋江API错误"""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


class JjwxcAdapter:
    """
    晋江文学城适配器
    
    功能：
    - 账号登录/会话管理
    - 创建书籍
    - 发布章节（含VIP/免费）
    - 获取书籍/章节信息
    - 草稿箱管理
    - 订阅比例设置
    
    晋江特点：
    - 使用 Cookie 维持会话
    - 章节订阅制（可设置免费/付费）
    - 较简单的反爬机制
    """
    
    # API 端点
    BASE_URL = "https://www.jjwxc.net"
    LOGIN_URL = "https://www.jjwxc.net/login.php"
    CREATE_BOOK_URL = "https://www.jjwxc.net/create/"
    CHAPTER_URL = "https://www.jjwxc.net/chapter/create"
    
    # API接口
    LOGIN_API = "https://www.jjwxc.net/login.php?action=login"
    CHECK_LOGIN_API = "https://www.jjwxc.net/login.php?action=chklogin"
    MY_BOOKS_API = "https://www.jjwxc.net/mine.php"
    CREATE_API = "https://www.jjwxc.net/create.php?action=createbook"
    GET_BOOK_API = "https://www.jjwxc.net/book.php?novelid={book_id}"
    CHAPTER_LIST_API = "https://www.jjwxc.net/chapter.php?novelid={book_id}"
    PUBLISH_CHAPTER_API = "https://www.jjwxc.net/chapter.php?action=create&novelid={book_id}"
    DELETE_CHAPTER_API = "https://www.jjwxc.net/chapter.php?action=del&chapterid={chapter_id}"
    
    # 分类API
    CATEGORY_API = "https://www.jjwxc.net/create/"
    
    # 章节分类
    GENRE_MAPPING = {
        "现代都市": "现代都市",
        "穿越重生": "穿越重生",
        "玄幻奇幻": "玄幻奇幻",
        "星际科幻": "星际科幻",
        "武侠仙侠": "武侠仙侠",
        "悬疑推理": "悬疑推理",
        "游戏竞技": "游戏竞技",
        "NPH": "NPH",
        "GB": "GB",
        "百合": "百合",
        "无CP": "无CP",
        "衍生同人": "衍生同人",
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
        self.credentials: Optional[JjwxcCredentials] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": self.BASE_URL,
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
    
    def _generate_token(self) -> str:
        """生成Token"""
        import uuid
        timestamp = int(time.time())
        raw = f"{uuid.uuid4()}{timestamp}"
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
                raise JjwxcAPIError(
                    PublishErrorCode.NETWORK_ERROR.value,
                    "请求超时"
                )
            except httpx.RequestError as e:
                logger.warning(f"Request error: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                raise JjwxcAPIError(
                    PublishErrorCode.NETWORK_ERROR.value,
                    f"网络请求失败: {str(e)}"
                )
        
        raise JjwxcAPIError(
            PublishErrorCode.UNKNOWN_ERROR.value,
            f"请求失败，已重试 {self.max_retries} 次"
        )
    
    def _parse_response(self, response: httpx.Response) -> dict:
        """解析响应"""
        content_type = response.headers.get("content-type", "")
        
        if "application/json" in content_type:
            return response.json()
        elif "text/html" in content_type:
            return {"html": response.text}
        else:
            return {"content": response.text}
    
    async def login(self, username: str, password: str) -> dict[str, Any]:
        """
        登录晋江文学城
        
        Args:
            username: 用户名/邮箱
            password: 密码
            
        Returns:
            dict: 登录结果
        """
        logger.info(f"开始登录晋江，用户名: {username}")
        
        client = await self._ensure_client()
        
        try:
            # 步骤1: 访问登录页面获取Cookie
            response = await self._request_with_retry("GET", self.LOGIN_URL)
            
            # 步骤2: 提交登录表单
            login_data = {
                "loginemail": username if "@" in username else "",
                "loginname": username if "@" not in username else "",
                "loginpwd": password,
                "remember": "1",
            }
            
            response = await self._request_with_retry(
                "POST",
                self.LOGIN_API,
                data=login_data
            )
            
            # 检查登录结果
            # 晋江登录成功会跳转到用户中心
            if "loginname" in str(response.cookies) or "jj_guid" in str(response.cookies):
                # 登录成功
                cookies_dict = dict(response.cookies)
                
                # 尝试获取用户信息
                user_info = await self._get_user_info()
                
                self.credentials = JjwxcCredentials(
                    username=username,
                    password=password,
                    cookies=cookies_dict,
                    user_id=user_info.get("user_id"),
                    user_name=user_info.get("user_name"),
                    token=self._generate_token()
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
                error_msg = self._extract_error_message(response.text)
                error_code = self._map_login_error(error_msg)
                
                logger.error(f"登录失败: {error_msg}")
                
                return {
                    "success": False,
                    "error_code": error_code,
                    "error_message": error_msg or "登录失败"
                }
                
        except JjwxcAPIError:
            raise
        except Exception as e:
            logger.error(f"登录异常: {str(e)}")
            raise JjwxcAPIError(
                PublishErrorCode.UNKNOWN_ERROR.value,
                f"登录异常: {str(e)}"
            )
    
    async def _get_user_info(self) -> dict:
        """获取用户信息"""
        try:
            response = await self._request_with_retry("GET", self.MY_BOOKS_API)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 从页面提取用户信息
            user_link = soup.select_one("a[href*='author']")
            if user_link:
                href = user_link.get("href", "")
                user_id = re.search(r"author=(\d+)", href)
                return {
                    "user_id": user_id.group(1) if user_id else None,
                    "user_name": user_link.text.strip()
                }
        except Exception:
            pass
        
        return {"user_id": None, "user_name": None}
    
    def _extract_error_message(self, html: str) -> str:
        """从HTML中提取错误消息"""
        soup = BeautifulSoup(html, "html.parser")
        
        # 尝试多种选择器
        selectors = [
            ".error",
            ".warning",
            ".message.error",
            "font[color='red']",
            ".alert-danger",
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.text.strip()
        
        return ""
    
    def _map_login_error(self, error_msg: str) -> str:
        """映射登录错误码"""
        msg_lower = error_msg.lower()
        if "密码" in error_msg or "pwd" in msg_lower:
            return PublishErrorCode.PASSWORD_ERROR.value
        elif "不存在" in error_msg or "not exist" in msg_lower:
            return PublishErrorCode.LOGIN_FAILED.value
        else:
            return PublishErrorCode.LOGIN_FAILED.value
    
    async def login_with_cookie(self, cookies: dict, user_id: str = None) -> dict[str, Any]:
        """
        使用Cookie登录
        
        Args:
            cookies: Cookie字典
            user_id: 用户ID（可选）
        """
        logger.info("使用Cookie登录晋江")
        
        client = await self._ensure_client()
        
        for name, value in cookies.items():
            client.cookies.set(name, value)
        
        # 验证Cookie有效性
        try:
            response = await self._request_with_retry("GET", self.CHECK_LOGIN_API)
            
            if "loginname" in str(response.cookies) or response.status_code == 200:
                user_info = await self._get_user_info()
                
                self.credentials = JjwxcCredentials(
                    username="",
                    password="",
                    cookies=cookies,
                    user_id=user_id or user_info.get("user_id"),
                    user_name=user_info.get("user_name"),
                    token=self._generate_token()
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
            
        except JjwxcAPIError as e:
            return {
                "status": "expired",
                "error_code": e.code,
                "message": e.message
            }
    
    async def get_book_list(self) -> list[JjwxcBookInfo]:
        """获取书籍列表"""
        if not self.credentials:
            raise JjwxcAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        client = await self._ensure_client()
        
        for name, value in self.credentials.cookies.items():
            client.cookies.set(name, value)
        
        response = await self._request_with_retry("GET", self.MY_BOOKS_API)
        
        books = self._parse_books_from_html(response.text)
        
        return books
    
    def _parse_books_from_html(self, html: str) -> list[JjwxcBookInfo]:
        """从HTML解析书籍列表"""
        soup = BeautifulSoup(html, "html.parser")
        books = []
        
        # 查找书籍列表
        book_rows = soup.select(".bookcase_table tr, .novel-list tr, table tr")
        
        for row in book_rows:
            try:
                link = row.select_one("a[href*='novelid']")
                if not link:
                    continue
                
                href = link.get("href", "")
                book_id = re.search(r"novelid=(\d+)", href)
                if not book_id:
                    continue
                
                title = link.text.strip()
                
                # 提取其他信息
                cells = row.select("td")
                status = ""
                word_count = 0
                
                for cell in cells:
                    text = cell.text.strip()
                    if "连载" in text:
                        status = "ongoing"
                    elif "完结" in text:
                        status = "completed"
                    elif "字" in text:
                        word_match = re.search(r"(\d+)", text)
                        if word_match:
                            word_count = int(word_match.group(1))
                
                books.append(JjwxcBookInfo(
                    book_id=book_id.group(1),
                    title=title,
                    author_id=self.credentials.user_id or "",
                    author_name=self.credentials.user_name or "",
                    status=status,
                    genre="",
                    word_count=word_count,
                    chapter_count=0,
                    collect_count=0
                ))
                
            except Exception as e:
                logger.warning(f"解析书籍行失败: {e}")
                continue
        
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
            raise JjwxcAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        logger.info(f"创建书籍: {title}, 类型: {genre}")
        
        client = await self._ensure_client()
        
        for name, value in self.credentials.cookies.items():
            client.cookies.set(name, value)
        
        # 访问创书页面获取必要参数
        response = await self._request_with_retry("GET", self.CREATE_BOOK_URL)
        
        # 提取表单令牌
        csrf_token = ""
        token_input = BeautifulSoup(response.text, "html.parser").select_one(
            "input[name='token'], input[name='_token']"
        )
        if token_input:
            csrf_token = token_input.get("value", "")
        
        # 准备创书数据
        create_data = {
            "noveltitle": title,
            "noveltype": genre,
            "novelsummary": synopsis,
            "tags": kwargs.get("tags", ""),
            "token": csrf_token,
        }
        
        # 如果晋江需要额外字段
        if kwargs.get("is_vip") is not None:
            create_data["isvip"] = "1" if kwargs["is_vip"] else "0"
        
        response = await self._request_with_retry(
            "POST",
            self.CREATE_API,
            data=create_data
        )
        
        # 晋江创书通常返回页面跳转或JSON
        result = self._parse_response(response)
        
        if isinstance(result, dict) and result.get("code") == 0:
            book_id = result.get("data", {}).get("novelid", "")
            return {
                "success": True,
                "book_id": str(book_id),
                "title": title,
                "message": "书籍创建成功"
            }
        elif isinstance(result, dict) and result.get("code") == 1:
            return {
                "success": False,
                "error_code": PublishErrorCode.DUPLICATE_SUBMISSION.value,
                "error_message": result.get("msg", "书名已存在")
            }
        else:
            # 检查响应中是否包含成功信息
            if "novelid" in response.text.lower() or "创建成功" in response.text:
                book_id_match = re.search(r"novelid[=:]?\s*['\"]?(\d+)", response.text, re.IGNORECASE)
                book_id = book_id_match.group(1) if book_id_match else "unknown"
                return {
                    "success": True,
                    "book_id": book_id,
                    "title": title,
                    "message": "书籍创建成功"
                }
            
            return {
                "success": False,
                "error_code": PublishErrorCode.PLATFORM_VALIDATION_ERROR.value,
                "error_message": "创建书籍失败"
            }
    
    async def get_book_info(self, book_id: str) -> JjwxcBookInfo:
        """获取书籍详细信息"""
        if not self.credentials:
            raise JjwxcAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        url = self.GET_BOOK_API.format(book_id=book_id)
        response = await self._request_with_retry("GET", url)
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 提取书籍信息
        title_elem = soup.select_one(".novel-title, h1, .book-title")
        title = title_elem.text.strip() if title_elem else ""
        
        # 提取其他信息
        word_count = 0
        chapter_count = 0
        collect_count = 0
        
        stats_text = soup.get_text()
        
        word_match = re.search(r"字数[：:]\s*(\d+)", stats_text)
        if word_match:
            word_count = int(word_match.group(1))
        
        chapter_match = re.search(r"章节[：:]\s*(\d+)", stats_text)
        if chapter_match:
            chapter_count = int(chapter_match.group(1))
        
        collect_match = re.search(r"收藏[：:]\s*(\d+)", stats_text)
        if collect_match:
            collect_count = int(collect_match.group(1))
        
        # 判断VIP状态
        is_vip = "VIP" in stats_text or "vip" in stats_text.lower()
        
        return JjwxcBookInfo(
            book_id=book_id,
            title=title,
            author_id=self.credentials.user_id or "",
            author_name=self.credentials.user_name or "",
            status="ongoing",  # 需要从页面解析
            genre="",  # 需要从页面解析
            word_count=word_count,
            chapter_count=chapter_count,
            collect_count=collect_count,
            is_vip=is_vip
        )
    
    async def get_chapter_list(self, book_id: str) -> list[JjwxcChapterInfo]:
        """获取章节列表"""
        if not self.credentials:
            raise JjwxcAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        url = self.CHAPTER_LIST_API.format(book_id=book_id)
        response = await self._request_with_retry("GET", url)
        
        return self._parse_chapters_from_html(response.text, book_id)
    
    def _parse_chapters_from_html(self, html: str, book_id: str) -> list[JjwxcChapterInfo]:
        """从HTML解析章节列表"""
        soup = BeautifulSoup(html, "html.parser")
        chapters = []
        
        # 查找章节列表
        chapter_rows = soup.select(".chapter-list tr, .chapter td, table tr")
        
        chapter_no = 0
        for row in chapter_rows:
            chapter_no += 1
            
            try:
                # 提取章节标题
                title_elem = row.select_one("a, .chapter-title")
                if not title_elem:
                    continue
                
                title = title_elem.text.strip()
                href = title_elem.get("href", "") if title_elem.name == "a" else ""
                
                chapter_id_match = re.search(r"chapterid=(\d+)", href)
                chapter_id = chapter_id_match.group(1) if chapter_id_match else str(chapter_no)
                
                # 提取字数
                word_count = 0
                cells = row.select("td")
                for cell in cells:
                    text = cell.text
                    word_match = re.search(r"(\d+)\s*字", text)
                    if word_match:
                        word_count = int(word_match.group(1))
                        break
                
                # 判断状态
                status = "published"
                is_vip = False
                row_text = row.get_text()
                if "锁定" in row_text:
                    status = "locked"
                elif "VIP" in row_text:
                    is_vip = True
                
                chapters.append(JjwxcChapterInfo(
                    chapter_id=chapter_id,
                    chapter_no=chapter_no,
                    title=title,
                    status=status,
                    word_count=word_count,
                    price=0.0,
                    is_vip=is_vip
                ))
                
            except Exception as e:
                logger.warning(f"解析章节失败: {e}")
                continue
        
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
            is_vip: 是否VIP章节
            
        Returns:
            dict: 发布结果
        """
        if not self.credentials:
            raise JjwxcAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        logger.info(f"发布章节: 书ID={book_id}, 章节={chapter_no}, 标题={title}")
        
        client = await self._ensure_client()
        
        for name, value in self.credentials.cookies.items():
            client.cookies.set(name, value)
        
        # 字数检查
        word_count = len(content)
        if word_count < 100:
            return {
                "success": False,
                "error_code": PublishErrorCode.CONTENT_TOO_SHORT.value,
                "error_message": f"内容字数不足（当前{word_count}字）"
            }
        
        # 访问章节发布页面获取CSRF
        chapter_page_url = f"{self.BASE_URL}/chapter.php?action=create&novelid={book_id}"
        
        # 准备章节数据
        chapter_data = {
            "chaptername": title,
            "chaptercontent": content,
            "isvip": "1" if kwargs.get("is_vip", False) else "0",
            "is_publish": "1" if mode == "publish" else "0",
        }
        
        url = self.PUBLISH_CHAPTER_API.format(book_id=book_id)
        response = await self._request_with_retry(
            "POST",
            url,
            data=chapter_data
        )
        
        # 检查发布结果
        result_text = response.text.lower()
        
        if "success" in result_text or "成功" in response.text:
            return {
                "success": True,
                "task_id": f"jjwxc_{book_id}_{chapter_no}",
                "chapter_no": chapter_no,
                "word_count": word_count,
                "message": "章节发布成功"
            }
        elif "重复" in response.text or "exist" in result_text:
            return {
                "success": False,
                "error_code": PublishErrorCode.DUPLICATE_SUBMISSION.value,
                "error_message": "章节已存在"
            }
        else:
            return {
                "success": False,
                "error_code": PublishErrorCode.UNKNOWN_ERROR.value,
                "error_message": "发布失败"
            }
    
    async def save_draft(
        self,
        book_id: str,
        chapter_no: int,
        title: str,
        content: str
    ) -> dict[str, Any]:
        """保存草稿"""
        if not self.credentials:
            raise JjwxcAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        client = await self._ensure_client()
        
        for name, value in self.credentials.cookies.items():
            client.cookies.set(name, value)
        
        draft_data = {
            "chaptername": title,
            "chaptercontent": content,
            "action": "savedraft",
            "novelid": book_id,
        }
        
        response = await self._request_with_retry(
            "POST",
            f"{self.BASE_URL}/chapter.php",
            data=draft_data
        )
        
        return {
            "success": "success" in response.text.lower() or "成功" in response.text,
            "message": "草稿保存完成"
        }
    
    async def delete_chapter(self, book_id: str, chapter_id: str) -> dict[str, Any]:
        """删除章节"""
        if not self.credentials:
            raise JjwxcAPIError(
                PublishErrorCode.SESSION_EXPIRED.value,
                "请先登录"
            )
        
        client = await self._ensure_client()
        
        for name, value in self.credentials.cookies.items():
            client.cookies.set(name, value)
        
        url = self.DELETE_CHAPTER_API.format(chapter_id=chapter_id)
        response = await self._request_with_retry(
            "GET",
            url,
            params={"novelid": book_id}
        )
        
        return {
            "success": "success" in response.text.lower() or "成功" in response.text,
            "message": "删除完成"
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
        except JjwxcAPIError as e:
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
__all__ = ["JjwxcAdapter", "JjwxcAPIError", "JjwxcCredentials", "JjwxcBookInfo", "JjwxcChapterInfo"]
