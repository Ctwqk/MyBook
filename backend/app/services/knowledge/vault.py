"""VaultManager - Obsidian Vault 管理

管理 Obsidian vault 的读写操作
"""
import os
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class VaultConfig:
    """Vault 配置"""
    vault_path: str
    embed_pattern: str = r"!\[\[(.*?)\]\]"  # Obsidian embed pattern
    link_pattern: str = r"\[\[(.*?)\]\]"     # Obsidian link pattern
    tag_pattern: str = r"#\w+"               # Tag pattern


@dataclass
class NoteMetadata:
    """笔记元数据"""
    path: str
    title: str
    tags: list[str]
    links: list[str]
    embeds: list[str]
    created: Optional[str] = None
    modified: Optional[str] = None


class VaultManager:
    """Obsidian Vault 管理器"""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.config = VaultConfig(vault_path=vault_path)
        
        # 确保 vault 目录存在
        self.vault_path.mkdir(parents=True, exist_ok=True)
    
    def _parse_frontmatter(self, content: str) -> tuple[dict, str]:
        """解析 YAML frontmatter"""
        frontmatter = {}
        body = content
        
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                # TODO: 使用 yaml 解析
                body = parts[2].strip()
        
        return frontmatter, body
    
    def _extract_metadata(self, path: str, content: str) -> NoteMetadata:
        """提取笔记元数据"""
        frontmatter, body = self._parse_frontmatter(content)
        
        # 提取标题
        title = path.stem.replace("-", " ").replace("_", " ").title()
        
        # 提取 tags
        tags = re.findall(self.config.tag_pattern, body)
        
        # 提取 links
        links = re.findall(self.config.link_pattern, body)
        links = [l.split("|")[0] for l in links]  # 处理 [[link|display]]
        
        # 提取 embeds
        embeds = re.findall(self.config.embed_pattern, body)
        embeds = [e.split("|")[0] for e in embeds]
        
        return NoteMetadata(
            path=str(path),
            title=frontmatter.get("title", title),
            tags=list(set(tags)),
            links=list(set(links)),
            embeds=list(set(embeds)),
            created=frontmatter.get("created"),
            modified=frontmatter.get("modified")
        )
    
    async def read_note(self, note_path: str) -> tuple[str, NoteMetadata]:
        """读取笔记"""
        full_path = self.vault_path / note_path
        
        if not full_path.suffix:
            full_path = full_path.with_suffix(".md")
        
        if not full_path.exists():
            raise FileNotFoundError(f"Note not found: {note_path}")
        
        content = full_path.read_text(encoding="utf-8")
        metadata = self._extract_metadata(full_path, content)
        
        return content, metadata
    
    async def write_note(
        self,
        note_path: str,
        content: str,
        frontmatter: Optional[dict] = None
    ) -> NoteMetadata:
        """写入笔记"""
        full_path = self.vault_path / note_path
        
        if not full_path.suffix:
            full_path = full_path.with_suffix(".md")
        
        # 确保父目录存在
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 添加 frontmatter
        if frontmatter:
            fm_lines = ["---"]
            for key, value in frontmatter.items():
                fm_lines.append(f"{key}: {value}")
            fm_lines.append("---\n")
            content = "\n".join(fm_lines) + content
        
        full_path.write_text(content, encoding="utf-8")
        
        return self._extract_metadata(full_path, content)
    
    async def delete_note(self, note_path: str) -> bool:
        """删除笔记"""
        full_path = self.vault_path / note_path
        
        if not full_path.suffix:
            full_path = full_path.with_suffix(".md")
        
        if full_path.exists():
            full_path.unlink()
            return True
        return False
    
    async def list_notes(self, folder: Optional[str] = None) -> list[str]:
        """列出笔记"""
        folder_path = self.vault_path / folder if folder else self.vault_path
        
        notes = []
        for path in folder_path.rglob("*.md"):
            rel_path = path.relative_to(self.vault_path)
            notes.append(str(rel_path))
        
        return sorted(notes)
    
    async def search_notes(self, query: str) -> list[str]:
        """搜索笔记"""
        results = []
        
        for path in self.vault_path.rglob("*.md"):
            content = path.read_text(encoding="utf-8").lower()
            if query.lower() in content:
                results.append(str(path.relative_to(self.vault_path)))
        
        return results
    
    async def get_backlinks(self, note_path: str) -> list[str]:
        """获取反向链接"""
        note_name = Path(note_path).stem
        backlinks = []
        
        for path in self.vault_path.rglob("*.md"):
            if path.stem == note_name:
                continue
            
            content = path.read_text(encoding="utf-8")
            links = re.findall(self.config.link_pattern, content)
            
            for link in links:
                link_name = link.split("|")[0]
                if link_name == note_name or link_name == note_path:
                    backlinks.append(str(path.relative_to(self.vault_path)))
                    break
        
        return backlinks
    
    async def sync_from_knowledge_graph(self, graph: "KnowledgeGraph") -> int:
        """
        从 KnowledgeGraph 同步到 Vault
        
        TODO: 实现同步逻辑
        """
        # TODO: 根据知识图谱生成 Obsidian 笔记
        return 0
    
    async def sync_to_knowledge_graph(self, graph: "KnowledgeGraph") -> int:
        """
        从 Vault 同步到 KnowledgeGraph
        
        TODO: 实现同步逻辑
        """
        # TODO: 解析 Obsidian 笔记，生成知识图谱
        return 0


# Forward reference
from app.services.knowledge.graph import KnowledgeGraph