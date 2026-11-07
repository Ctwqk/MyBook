"""IndexService - 索引服务

为知识库建立全文索引，支持语义搜索
"""
from typing import Optional
from dataclasses import dataclass
import json


@dataclass
class SearchResult:
    """搜索结果"""
    id: str
    content: str
    score: float
    metadata: dict


class IndexService:
    """
    知识库索引服务
    
    支持：
    - 全文搜索
    - 语义搜索（需要 LLM embedding）
    - 过滤和排序
    """
    
    def __init__(self):
        self._index = {}  # id -> {content, embedding, metadata}
    
    async def index_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> None:
        """索引文档"""
        self._index[doc_id] = {
            "content": content,
            "metadata": metadata or {},
            "embedding": None  # TODO: 生成 embedding
        }
    
    async def remove_document(self, doc_id: str) -> bool:
        """移除文档"""
        if doc_id in self._index:
            del self._index[doc_id]
            return True
        return False
    
    async def search(
        self,
        query: str,
        filters: Optional[dict] = None,
        limit: int = 10
    ) -> list[SearchResult]:
        """
        搜索文档
        
        Args:
            query: 搜索查询
            filters: 过滤条件
            limit: 返回数量
        
        Returns:
            搜索结果列表
        """
        results = []
        query_lower = query.lower()
        
        for doc_id, doc in self._index.items():
            # 应用过滤
            if filters:
                match = True
                for key, value in filters.items():
                    if doc["metadata"].get(key) != value:
                        match = False
                        break
                if not match:
                    continue
            
            # 简单关键词匹配
            content = doc["content"].lower()
            if query_lower in content:
                # 计算简单相关性分数
                score = content.count(query_lower) / max(len(content), 1) * 100
                results.append(SearchResult(
                    id=doc_id,
                    content=doc["content"][:500],  # 截取前500字符
                    score=score,
                    metadata=doc["metadata"]
                ))
        
        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:limit]
    
    async def semantic_search(
        self,
        query: str,
        limit: int = 10
    ) -> list[SearchResult]:
        """
        语义搜索
        
        TODO: 需要集成 LLM embedding 模型
        """
        # TODO: 生成查询 embedding
        # TODO: 计算余弦相似度
        # TODO: 返回排序结果
        
        # 目前回退到关键词搜索
        return await self.search(query, limit=limit)
    
    async def get_document(self, doc_id: str) -> Optional[dict]:
        """获取文档"""
        return self._index.get(doc_id)
    
    async def get_stats(self) -> dict:
        """获取索引统计"""
        return {
            "total_documents": len(self._index),
            "indexed_content_size": sum(
                len(doc["content"]) for doc in self._index.values()
            )
        }