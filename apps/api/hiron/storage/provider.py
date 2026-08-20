"""Storage provider abstraction interface and implementations for Supabase storage per Engineering Guidelines §11."""

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


class SupabaseStorageProvider(StorageProvider):
    """Supabase storage provider using REST API for serverless environments."""

    def __init__(
        self,
        supabase_url: str,
        supabase_service_role_key: str,
        bucket_name: str = "resumes",
    ) -> None:
        if not supabase_url or not supabase_service_role_key:
            raise ValueError("supabase_url and supabase_service_role_key are required")

        self.supabase_url = supabase_url.rstrip("/")
        self.bucket_name = bucket_name
        self.base_url = f"{self.supabase_url}/storage/v1/object"
        if supabase_service_role_key.startswith("sb_secret_"):
            self.headers = {
                "apikey": supabase_service_role_key,
            }
        else:
            self.headers = {
                "Authorization": f"Bearer {supabase_service_role_key}",
                "apikey": supabase_service_role_key,
            }

    async def upload_file(
        self,
        tenant_id: uuid.UUID,
        key: str,
        file_data: bytes,
        content_type: str,
    ) -> str:
        """Upload file content to Supabase Storage."""
        import httpx

        path = f"{tenant_id}/{key.lstrip('/')}"
        url = f"{self.base_url}/{self.bucket_name}/{path}"

        headers = {**self.headers, "Content-Type": content_type}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, content=file_data, headers=headers)
            response.raise_for_status()

        return f"{self.base_url}/public/{self.bucket_name}/{path}"

    async def download_file(
        self,
        tenant_id: uuid.UUID,
        key: str,
    ) -> bytes:
        """Retrieve raw file content bytes from Supabase Storage."""
        import httpx

        path = f"{tenant_id}/{key.lstrip('/')}"
        url = f"{self.base_url}/authenticated/{self.bucket_name}/{path}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.content

    async def delete_file(
        self,
        tenant_id: uuid.UUID,
        key: str,
    ) -> bool:
        """Remove file from Supabase Storage."""
        import httpx

        path = f"{tenant_id}/{key.lstrip('/')}"
        url = f"{self.base_url}/{self.bucket_name}/{path}"

        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=self.headers)
            return response.status_code == 200

    async def generate_presigned_url(
        self,
        tenant_id: uuid.UUID,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate download URL via Supabase Storage sign endpoint."""
        import httpx

        path = f"{tenant_id}/{key.lstrip('/')}"
        url = f"{self.base_url}/sign/{self.bucket_name}/{path}"

        payload = {"expiresIn": expires_in}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            # The signedURL path returned by Supabase typically starts with '/object/sign/...'
            return f"{self.supabase_url}/storage/v1{data['signedURL']}"
