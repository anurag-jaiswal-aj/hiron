"""Unit tests for storage providers and file validation routines."""

import tempfile
import uuid

import pytest

from hiron.resumes.exceptions import FileTooLargeError, UnsupportedFileTypeError
from hiron.resumes.service import ResumeService
from hiron.storage.provider import LocalStorageProvider, SupabaseStorageProvider


@pytest.mark.asyncio
async def test_local_storage_provider_lifecycle() -> None:
    """Verify upload, download, presigned URL, and delete operations on LocalStorageProvider."""
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = LocalStorageProvider(base_path=tmpdir)
        tenant_id = uuid.uuid4()
        key = "resumes/test_resume.pdf"
        data = b"%PDF-1.4 sample content"

        file_uri = await provider.upload_file(tenant_id, key, data, "application/pdf")
        assert file_uri is not None

        downloaded = await provider.download_file(tenant_id, key)
        assert downloaded == data

        url = await provider.generate_presigned_url(tenant_id, key)
        assert "file://" in url

        deleted = await provider.delete_file(tenant_id, key)
        assert deleted is True

        with pytest.raises(FileNotFoundError):
            await provider.download_file(tenant_id, key)


@pytest.mark.asyncio
async def test_supabase_storage_provider_initialization_validates_args() -> None:
    """Verify initialization requires url and key."""
    with pytest.raises(ValueError, match="required"):
        SupabaseStorageProvider(supabase_url="", supabase_service_role_key="")


@pytest.mark.asyncio
async def test_supabase_storage_provider_mock() -> None:
    """Verify SupabaseStorageProvider methods via httpx mocking."""
    from unittest.mock import MagicMock, patch

    provider = SupabaseStorageProvider(
        supabase_url="https://xyz.supabase.co",
        supabase_service_role_key="secret-key",
        bucket_name="my-bucket",
    )
    tenant_id = uuid.uuid4()
    key = "test_file.pdf"

    # 1. Test Upload
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        uri = await provider.upload_file(
            tenant_id,
            key,
            b"dummy",
            "application/pdf",
        )
        assert uri.startswith("https://xyz.supabase.co/storage/v1/object/public/my-bucket/")
        assert str(tenant_id) in uri
        assert mock_post.called

    # 2. Test Download
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"content"
        mock_get.return_value = mock_response

        content = await provider.download_file(tenant_id, key)
        assert content == b"content"
        assert mock_get.called

    # 3. Test Delete
    with patch("httpx.AsyncClient.delete") as mock_delete:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response

        result = await provider.delete_file(tenant_id, key)
        assert result is True

    # 4. Test Presigned URL
    with patch("httpx.AsyncClient.post") as mock_post_sign:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "signedURL": "/object/sign/my-bucket/123/test.pdf?token=abc"
        }
        mock_post_sign.return_value = mock_response

        url = await provider.generate_presigned_url(tenant_id, key)
        assert (
            url == "https://xyz.supabase.co/storage/v1/object/sign/my-bucket/123/test.pdf?token=abc"
        )
        assert mock_post_sign.called


def test_file_validation_success() -> None:
    """Verify valid PDF, DOCX, and TXT files pass validation."""
    service = ResumeService()
    service.validate_file("resume.pdf", "application/pdf", 1024)
    service.validate_file(
        "document.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        2048,
    )
    service.validate_file("plain.txt", "text/plain", 512)


def test_file_validation_too_large_raises_413() -> None:
    """Verify file exceeding 10 MB limit raises FileTooLargeError."""
    service = ResumeService()
    large_size = 10 * 1024 * 1024 + 1
    with pytest.raises(FileTooLargeError):
        service.validate_file("huge_resume.pdf", "application/pdf", large_size)


def test_file_validation_unsupported_type_raises_415() -> None:
    """Verify unsupported MIME type and extension raise UnsupportedFileTypeError."""
    service = ResumeService()
    with pytest.raises(UnsupportedFileTypeError):
        service.validate_file("photo.png", "image/png", 1024)
    with pytest.raises(UnsupportedFileTypeError):
        service.validate_file("archive.zip", "application/zip", 1024)
