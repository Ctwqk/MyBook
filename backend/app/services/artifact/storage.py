"""
Artifact Storage Service - v2.3

支持：
- MinIO 对象存储
- 项目级路径隔离
- Artifact 版本管理
"""
import io
from typing import Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ArtifactStorage:
    """
    Artifact 存储服务 - v2.3 多项目隔离
    
    使用 MinIO 进行对象存储，所有路径按 project_id 隔离
    """
    
    # 路径模板 - 确保项目隔离
    PATH_TEMPLATE = "projects/{project_id}/artifacts/{artifact_type}/{timestamp}/{filename}"
    
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str = "mybook-artifacts",
        secure: bool = True
    ):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.secure = secure
        self._client = None
    
    async def _get_client(self):
        """获取 MinIO 客户端"""
        if self._client is None:
            try:
                from minio import AsyncMinio
                self._client = AsyncMinio(
                    endpoint=self.endpoint,
                    access_key=self.access_key,
                    secret_key=self.secret_key,
                    secure=self.secure
                )
            except ImportError:
                raise RuntimeError("MinIO client not installed. Run: pip install minio")
        return self._client
    
    def _make_project_path(
        self,
        project_id: int,
        artifact_type: str,
        filename: str
    ) -> str:
        """
        生成项目隔离的存储路径
        
        格式: projects/{project_id}/artifacts/{artifact_type}/{timestamp}/{filename}
        
        确保：
        1. 不同项目的 artifact 完全隔离
        2. 按 artifact_type 分类
        3. 带时间戳版本区分
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"projects/{project_id}/artifacts/{artifact_type}/{timestamp}/{filename}"
    
    async def upload_artifact(
        self,
        project_id: int,
        artifact_type: str,
        filename: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        上传 artifact（带项目隔离）
        
        Args:
            project_id: 项目 ID - 用于路径隔离
            artifact_type: artifact 类型（如 chapter_draft, review_report, etc.）
            filename: 文件名
            data: 文件内容
            content_type: MIME 类型
            metadata: 额外元数据
        
        Returns:
            上传结果包含存储路径和 URL
        """
        client = await self._get_client()
        
        # 确保 bucket 存在
        try:
            await client.bucket_exists(self.bucket)
        except Exception:
            await client.make_bucket(self.bucket)
        
        # 生成项目隔离路径
        object_name = self._make_project_path(project_id, artifact_type, filename)
        
        # 准备 metadata
        user_metadata = {
            "project_id": str(project_id),
            "artifact_type": artifact_type,
            "created_at": datetime.now().isoformat(),
        }
        if metadata:
            user_metadata.update({k: str(v) for k, v in metadata.items()})
        
        # 上传
        await client.put_object(
            bucket_name=self.bucket,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
            metadata=user_metadata
        )
        
        # 生成访问 URL（预设签名 URL，1小时有效期）
        url = await client.presigned_get_object(
            bucket_name=self.bucket,
            object_name=object_name,
            expires=datetime.timedelta(hours=1)
        )
        
        return {
            "success": True,
            "object_name": object_name,
            "url": url,
            "project_id": project_id,
            "artifact_type": artifact_type,
            "size": len(data),
            "metadata": user_metadata
        }
    
    async def download_artifact(
        self,
        project_id: int,
        artifact_type: str,
        filename: str,
        version_id: Optional[str] = None
    ) -> Optional[bytes]:
        """
        下载 artifact（带项目隔离验证）
        
        下载时会验证存储路径中的 project_id 确保隔离
        """
        client = await self._get_client()
        
        # 构建路径（使用最新版本）
        # 实际应该通过 list_objects 找到对应文件
        prefix = f"projects/{project_id}/artifacts/{artifact_type}/"
        
        try:
            # 列出匹配的对象
            objects = await client.list_objects(
                self.bucket,
                prefix=prefix,
                recursive=True
            )
            
            # 找到匹配的文件
            target_object = None
            for obj in objects:
                if obj.object_name.endswith(f"/{filename}"):
                    target_object = obj.object_name
                    break
            
            if not target_object:
                return None
            
            # 验证路径中的 project_id（双重保险）
            path_parts = target_object.split("/")
            if len(path_parts) < 2 or path_parts[1] != str(project_id):
                logger.warning(f"Project isolation violation attempt: {target_object}")
                return None
            
            # 下载
            response = await client.get_object(
                self.bucket,
                target_object,
                version_id=version_id
            )
            return await response.read()
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
    
    async def list_artifacts(
        self,
        project_id: int,
        artifact_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        列出项目的 artifacts（只返回属于该项目的）
        
        确保多项目隔离
        """
        client = await self._get_client()
        
        # 构建前缀 - 强制项目隔离
        if artifact_type:
            prefix = f"projects/{project_id}/artifacts/{artifact_type}/"
        else:
            prefix = f"projects/{project_id}/"
        
        try:
            objects = await client.list_objects(
                self.bucket,
                prefix=prefix,
                recursive=False  # 只列出顶层
            )
            
            artifacts = []
            for obj in objects:
                # 验证 project_id
                path_parts = obj.object_name.split("/")
                if len(path_parts) >= 2 and path_parts[1] == str(project_id):
                    artifacts.append({
                        "object_name": obj.object_name,
                        "size": obj.size,
                        "last_modified": obj.last_modified,
                        "etag": obj.etag
                    })
            
            return artifacts
            
        except Exception as e:
            logger.error(f"List failed: {e}")
            return []
    
    async def delete_artifact(
        self,
        project_id: int,
        artifact_type: str,
        filename: str
    ) -> bool:
        """
        删除 artifact（带项目隔离验证）
        """
        client = await self._get_client()
        
        prefix = f"projects/{project_id}/artifacts/{artifact_type}/"
        
        try:
            objects = await client.list_objects(
                self.bucket,
                prefix=prefix,
                recursive=True
            )
            
            for obj in objects:
                if obj.object_name.endswith(f"/{filename}"):
                    # 验证 project_id
                    path_parts = obj.object_name.split("/")
                    if len(path_parts) >= 2 and path_parts[1] == str(project_id):
                        await client.remove_object(self.bucket, obj.object_name)
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False
    
    async def delete_project_artifacts(self, project_id: int) -> int:
        """
        删除项目的所有 artifacts（项目删除时调用）
        
        确保彻底清理所有关联数据
        """
        client = await self._get_client()
        
        prefix = f"projects/{project_id}/"
        deleted_count = 0
        
        try:
            objects = await client.list_objects(
                self.bucket,
                prefix=prefix,
                recursive=True
            )
            
            for obj in objects:
                # 验证 project_id
                path_parts = obj.object_name.split("/")
                if len(path_parts) >= 2 and path_parts[1] == str(project_id):
                    await client.remove_object(self.bucket, obj.object_name)
                    deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Delete project artifacts failed: {e}")
            return deleted_count


# 配置管理
class ArtifactStorageManager:
    """Artifact 存储管理器"""
    
    _instances: dict[int, ArtifactStorage] = {}
    
    @classmethod
    def get_storage(
        cls,
        project_id: int,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None
    ) -> ArtifactStorage:
        """
        获取项目的 artifact 存储实例
        
        每个项目使用独立的存储实例，但共享 MinIO 连接
        """
        if project_id not in cls._instances:
            # 从配置获取或使用默认值
            from app.core.config import get_settings
            settings = get_settings()
            
            cls._instances[project_id] = ArtifactStorage(
                endpoint=endpoint or getattr(settings, 'minio_endpoint', 'localhost:9000'),
                access_key=access_key or getattr(settings, 'minio_access_key', 'minioadmin'),
                secret_key=secret_key or getattr(settings, 'minio_secret_key', 'minioadmin'),
                bucket=getattr(settings, 'minio_bucket', 'mybook-artifacts'),
                secure=getattr(settings, 'minio_secure', True)
            )
        
        return cls._instances[project_id]
    
    @classmethod
    def clear_storage(cls, project_id: int):
        """清理项目的存储实例"""
        if project_id in cls._instances:
            del cls._instances[project_id]
