"""
Redis Cache Service - v2.3

支持：
- Redis 缓存
- 项目级 key 隔离
- 缓存自动过期
"""
import json
from typing import Optional, Any
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis 缓存服务 - v2.3 多项目隔离
    
    所有 key 都以 project_id 为前缀，确保项目间完全隔离
    """
    
    # Key 前缀模板 - 确保项目隔离
    KEY_PREFIX = "mybook:project:{project_id}:{category}:{key}"
    
    # 全局 key 前缀（不涉及项目隔离的元数据）
    GLOBAL_PREFIX = "mybook:global:{category}:{key}"
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.decode_responses = decode_responses
        self._client = None
    
    async def _get_client(self):
        """获取 Redis 客户端"""
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=self.decode_responses
                )
            except ImportError:
                raise RuntimeError("Redis client not installed. Run: pip install redis")
        return self._client
    
    def _make_project_key(self, project_id: int, category: str, key: str) -> str:
        """
        生成项目隔离的缓存 key
        
        格式: mybook:project:{project_id}:{category}:{key}
        
        确保不同项目的缓存完全隔离
        """
        return f"mybook:project:{project_id}:{category}:{key}"
    
    def _make_global_key(self, category: str, key: str) -> str:
        """生成全局 key（不涉及项目隔离）"""
        return f"mybook:global:{category}:{key}"
    
    # ==================== 基础操作 ====================
    
    async def get(self, project_id: int, category: str, key: str) -> Optional[Any]:
        """获取缓存值（带项目隔离）"""
        client = await self._get_client()
        full_key = self._make_project_key(project_id, category, key)
        
        try:
            value = await client.get(full_key)
            if value is None:
                return None
            
            # 尝试 JSON 反序列化
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Cache get failed: {e}")
            return None
    
    async def set(
        self,
        project_id: int,
        category: str,
        key: str,
        value: Any,
        expire_seconds: Optional[int] = None
    ) -> bool:
        """设置缓存值（带项目隔离）"""
        client = await self._get_client()
        full_key = self._make_project_key(project_id, category, key)
        
        try:
            # 尝试 JSON 序列化
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value)
            elif not isinstance(value, str):
                value = str(value)
            
            if expire_seconds:
                await client.setex(full_key, expire_seconds, value)
            else:
                await client.set(full_key, value)
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set failed: {e}")
            return False
    
    async def delete(self, project_id: int, category: str, key: str) -> bool:
        """删除缓存（带项目隔离）"""
        client = await self._get_client()
        full_key = self._make_project_key(project_id, category, key)
        
        try:
            result = await client.delete(full_key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete failed: {e}")
            return False
    
    async def exists(self, project_id: int, category: str, key: str) -> bool:
        """检查 key 是否存在（带项目隔离）"""
        client = await self._get_client()
        full_key = self._make_project_key(project_id, category, key)
        
        try:
            return await client.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Cache exists check failed: {e}")
            return False
    
    # ==================== 批量操作 ====================
    
    async def get_many(
        self,
        project_id: int,
        category: str,
        keys: list[str]
    ) -> dict[str, Optional[Any]]:
        """批量获取缓存（带项目隔离）"""
        client = await self._get_client()
        full_keys = [self._make_project_key(project_id, category, k) for k in keys]
        
        try:
            values = await client.mget(full_keys)
            result = {}
            for i, key in enumerate(keys):
                value = values[i]
                if value is None:
                    result[key] = None
                else:
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = value
            return result
        except Exception as e:
            logger.error(f"Cache mget failed: {e}")
            return {k: None for k in keys}
    
    async def set_many(
        self,
        project_id: int,
        category: str,
        items: dict[str, Any],
        expire_seconds: Optional[int] = None
    ) -> int:
        """批量设置缓存（带项目隔离）"""
        client = await self._get_client()
        
        try:
            pipeline = client.pipeline()
            
            for key, value in items.items():
                full_key = self._make_project_key(project_id, category, key)
                
                if isinstance(value, (dict, list, tuple)):
                    value = json.dumps(value)
                elif not isinstance(value, str):
                    value = str(value)
                
                if expire_seconds:
                    pipeline.setex(full_key, expire_seconds, value)
                else:
                    pipeline.set(full_key, value)
            
            results = await pipeline.execute()
            return sum(1 for r in results if r)
            
        except Exception as e:
            logger.error(f"Cache mset failed: {e}")
            return 0
    
    async def delete_pattern(self, project_id: int, category: str, pattern: str) -> int:
        """
        按模式删除缓存（带项目隔离）
        
        例如：delete_pattern(1, "llm", "*") 删除项目 1 的所有 llm 缓存
        """
        client = await self._get_client()
        full_pattern = self._make_project_key(project_id, category, pattern)
        
        try:
            # 使用 SCAN 而非 KEYS（生产环境更安全）
            cursor = 0
            deleted_count = 0
            
            while True:
                cursor, keys = await client.scan(cursor, match=full_pattern, count=100)
                
                if keys:
                    deleted_count += await client.delete(*keys)
                
                if cursor == 0:
                    break
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache delete pattern failed: {e}")
            return 0
    
    # ==================== 项目级清理 ====================
    
    async def clear_project_cache(self, project_id: int) -> int:
        """
        清除项目的所有缓存（项目删除时调用）
        
        确保彻底清理所有关联数据
        """
        client = await self._get_client()
        prefix = f"mybook:project:{project_id}:"
        
        try:
            cursor = 0
            deleted_count = 0
            
            while True:
                cursor, keys = await client.scan(cursor, match=f"{prefix}*", count=100)
                
                if keys:
                    deleted_count += await client.delete(*keys)
                
                if cursor == 0:
                    break
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Clear project cache failed: {e}")
            return deleted_count
    
    # ==================== TTL 操作 ====================
    
    async def get_ttl(self, project_id: int, category: str, key: str) -> int:
        """获取 key 的剩余 TTL（秒）"""
        client = await self._get_client()
        full_key = self._make_project_key(project_id, category, key)
        
        try:
            return await client.ttl(full_key)
        except Exception as e:
            logger.error(f"Get TTL failed: {e}")
            return -1
    
    async def expire(self, project_id: int, category: str, key: str, seconds: int) -> bool:
        """设置 key 的过期时间"""
        client = await self._get_client()
        full_key = self._make_project_key(project_id, category, key)
        
        try:
            return await client.expire(full_key, seconds)
        except Exception as e:
            logger.error(f"Set expire failed: {e}")
            return False
    
    # ==================== 计数器操作 ====================
    
    async def incr(self, project_id: int, category: str, key: str, amount: int = 1) -> int:
        """递增计数器（带项目隔离）"""
        client = await self._get_client()
        full_key = self._make_project_key(project_id, category, key)
        
        try:
            return await client.incr(full_key, amount)
        except Exception as e:
            logger.error(f"Incr failed: {e}")
            return 0
    
    async def decr(self, project_id: int, category: str, key: str, amount: int = 1) -> int:
        """递减计数器（带项目隔离）"""
        client = await self._get_client()
        full_key = self._make_project_key(project_id, category, key)
        
        try:
            return await client.decr(full_key, amount)
        except Exception as e:
            logger.error(f"Decr failed: {e}")
            return 0


# 预定义的缓存分类
class CacheCategory:
    """缓存分类常量"""
    LLM_CALLS = "llm_calls"           # LLM 调用记录
    API_RESPONSE = "api_response"      # API 响应缓存
    QUERY_RESULT = "query_result"     # 查询结果缓存
    SESSION = "session"               # 会话数据
    LOCK = "lock"                     # 分布式锁
    RATE_LIMIT = "rate_limit"          # 速率限制
    USER_PREF = "user_pref"            # 用户偏好


# 缓存管理器
class CacheManager:
    """缓存管理器 - 支持多项目"""
    
    _instances: dict[int, RedisCache] = {}
    
    @classmethod
    def get_cache(
        cls,
        project_id: int,
        host: Optional[str] = None,
        port: Optional[int] = None
    ) -> RedisCache:
        """
        获取项目的缓存实例
        
        每个项目使用独立的 Redis 连接
        """
        if project_id not in cls._instances:
            from app.core.config import get_settings
            settings = get_settings()
            
            cls._instances[project_id] = RedisCache(
                host=host or getattr(settings, 'redis_host', 'localhost'),
                port=port or getattr(settings, 'redis_port', 6379),
                db=getattr(settings, 'redis_db', 0),
                password=getattr(settings, 'redis_password', None)
            )
        
        return cls._instances[project_id]
    
    @classmethod
    def clear_cache(cls, project_id: int):
        """清理项目的缓存实例"""
        if project_id in cls._instances:
            del cls._instances[project_id]
