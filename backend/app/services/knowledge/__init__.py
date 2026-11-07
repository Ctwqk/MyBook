"""Knowledge Services - 知识系统 V4.6

提供：
- KnowledgeGraph: 知识图谱管理
- VaultManager: Obsidian Vault 管理
- IndexService: 索引服务
"""
from app.services.knowledge.graph import KnowledgeGraph
from app.services.knowledge.vault import VaultManager
from app.services.knowledge.indexer import IndexService

__all__ = [
    "KnowledgeGraph",
    "VaultManager",
    "IndexService",
]