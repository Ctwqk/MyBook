"""Platform Adapter - 平台适配器接口"""
from abc import ABC, abstractmethod
from typing import Any, Optional

from app.models.publish_task import PublishErrorCode


class PlatformAdapter(ABC):
    """平台适配器抽象基类"""
    
    @abstractmethod
    async def register_session(
        self,
        session_token: str,
        extra_data: Optional[dict] = None
    ) -> dict[str, Any]:
        """注册会话"""
        pass
    
    @abstractmethod
    async def get_account_status(self, account_id: str) -> dict[str, Any]:
        """获取账户状态"""
        pass
    
    @abstractmethod
    async def bind_book(
        self,
        account_id: str,
        remote_book_id: str,
        book_title: str,
        extra_data: Optional[dict] = None
    ) -> dict[str, Any]:
        """绑定书籍"""
        pass
    
    @abstractmethod
    async def publish_chapter(
        self,
        account_id: str,
        book_id: str,
        chapter_no: int,
        title: str,
        content: str,
        mode: str
    ) -> dict[str, Any]:
        """发布章节"""
        pass
    
    @abstractmethod
    async def get_task_status(self, account_id: str, task_id: str) -> dict[str, Any]:
        """获取任务状态"""
        pass


class MockPlatformAdapter(PlatformAdapter):
    """Mock 平台适配器 - 用于测试"""
    
    def __init__(self):
        self.accounts = {}
        self.books = {}
        self.tasks = {}
    
    async def register_session(
        self,
        session_token: str,
        extra_data: Optional[dict] = None
    ) -> dict[str, Any]:
        """Mock 注册会话"""
        import random
        account_id = f"mock_account_{len(self.accounts) + 1}"
        self.accounts[account_id] = {
            "status": "active",
            "session_token": session_token,
            "bound_books": []
        }
        return {
            "account_id": account_id,
            "status": "active",
            "bound_books": []
        }
    
    async def get_account_status(self, account_id: str) -> dict[str, Any]:
        """Mock 获取账户状态"""
        account = self.accounts.get(account_id, {})
        return {
            "status": account.get("status", "unknown"),
            "bound_books": account.get("bound_books", [])
        }
    
    async def bind_book(
        self,
        account_id: str,
        remote_book_id: str,
        book_title: str,
        extra_data: Optional[dict] = None
    ) -> dict[str, Any]:
        """Mock 绑定书籍"""
        book_key = f"{account_id}:{remote_book_id}"
        self.books[book_key] = {
            "title": book_title,
            "bound": True
        }
        
        if account_id in self.accounts:
            if remote_book_id not in self.accounts[account_id].get("bound_books", []):
                self.accounts[account_id].setdefault("bound_books", []).append(remote_book_id)
        
        return {
            "local_book_id": None,
            "bound": True
        }
    
    async def publish_chapter(
        self,
        account_id: str,
        book_id: str,
        chapter_no: int,
        title: str,
        content: str,
        mode: str
    ) -> dict[str, Any]:
        """Mock 发布章节"""
        import random
        success = random.random() > 0.1
        
        if success:
            return {
                "success": True,
                "task_id": f"mock_task_{chapter_no}",
                "message": f"Chapter {chapter_no} published successfully"
            }
        else:
            return {
                "success": False,
                "error_code": PublishErrorCode.NETWORK_ERROR.value,
                "error_message": "Mock: Network error occurred"
            }
    
    async def get_task_status(self, account_id: str, task_id: str) -> dict[str, Any]:
        """Mock 获取任务状态"""
        return {
            "status": "success",
            "message": "Task completed"
        }
