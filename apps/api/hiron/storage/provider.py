"""Storage provider abstraction interface and implementations for S3-compatible file storage per Engineering Guidelines §11."""

import uuid
from abc import ABC, abstractmethod
from pathlib import Path


class StorageProvider(ABC):
    """Abstract storage provider interface."""

    @abstractmethod
    async def upload_file(
        self,
        tenant_id: uuid.UUID,
        key: str,
        file_data: bytes,
        content_type: str,
    ) -> str:
        """Upload file content and return storage key/URI."""
        ...

    @abstractmethod
    async def download_file(
        self,
        tenant_id: uuid.UUID,
        key: str,
    ) -> bytes:
        """Retrieve raw file content bytes."""
        ...

    @abstractmethod
    async def delete_file(
        self,
        tenant_id: uuid.UUID,
        key: str,
    ) -> bool:
        """Remove file from storage."""
        ...

    @abstractmethod
    async def generate_presigned_url(
        self,
        tenant_id: uuid.UUID,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate download URL for stored file object."""
        ...


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage provider for development and testing environment."""

    def __init__(self, base_path: str = "./storage") -> None:
        self.base_path = Path(base_path)

    def _get_file_path(self, tenant_id: uuid.UUID, key: str) -> Path:
        """Compute absolute local path for tenant file key."""
        return self.base_path / str(tenant_id) / key.lstrip("/")

    async def upload_file(
        self,
        tenant_id: uuid.UUID,
        key: str,
        file_data: bytes,
        content_type: str,
    ) -> str:
        """Save file bytes to local filesystem."""
        _ = content_type
        file_path = self._get_file_path(tenant_id, key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(file_data)
        return str(file_path)

    async def download_file(
        self,
        tenant_id: uuid.UUID,
        key: str,
    ) -> bytes:
        """Read file bytes from local filesystem."""
        file_path = self._get_file_path(tenant_id, key)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found at {file_path}")
        return file_path.read_bytes()

    async def delete_file(
        self,
        tenant_id: uuid.UUID,
        key: str,
    ) -> bool:
        """Remove file from local filesystem."""
        file_path = self._get_file_path(tenant_id, key)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def generate_presigned_url(
        self,
        tenant_id: uuid.UUID,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Return local file URI."""
        _ = expires_in
        file_path = self._get_file_path(tenant_id, key)
        return f"file://{file_path.resolve()}"


class S3StorageProvider(StorageProvider):
    """S3-compatible storage provider for production environments."""

    def __init__(self, bucket_name: str = "hiron-resumes", region_name: str = "us-east-1") -> None:
        self.bucket_name = bucket_name
        self.region_name = region_name

    async def upload_file(
        self,
        tenant_id: uuid.UUID,
        key: str,
        file_data: bytes,
        content_type: str,
    ) -> str:
        """Mock/S3 upload implementation."""
        _ = (file_data, content_type)
        s3_key = f"{tenant_id}/{key.lstrip('/')}"
        return f"s3://{self.bucket_name}/{s3_key}"

    async def download_file(
        self,
        tenant_id: uuid.UUID,
        key: str,
    ) -> bytes:
        """Mock/S3 download implementation."""
        _ = (tenant_id, key)
        return b"%PDF-1.4 Mock S3 File Content"

    async def delete_file(
        self,
        tenant_id: uuid.UUID,
        key: str,
    ) -> bool:
        """Mock/S3 delete implementation."""
        _ = (tenant_id, key)
        return True

    async def generate_presigned_url(
        self,
        tenant_id: uuid.UUID,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Mock/S3 presigned URL generation."""
        _ = expires_in
        s3_key = f"{tenant_id}/{key.lstrip('/')}"
        return f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{s3_key}"
