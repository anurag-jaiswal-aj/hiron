"""Unit tests for storage providers and file validation routines."""

import tempfile
import uuid

import pytest

from hiron.resumes.exceptions import FileTooLargeError, UnsupportedFileTypeError
from hiron.resumes.service import ResumeService
from hiron.storage.provider import LocalStorageProvider, S3StorageProvider


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
async def test_s3_storage_provider_mock() -> None:
    """Verify S3StorageProvider methods."""
    provider = S3StorageProvider(bucket_name="my-bucket", region_name="us-west-2")
    tenant_id = uuid.uuid4()
    key = "test_file.docx"

    uri = await provider.upload_file(
        tenant_id,
        key,
        b"dummy",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert uri.startswith("s3://my-bucket/")

    url = await provider.generate_presigned_url(tenant_id, key)
    assert "s3.us-west-2.amazonaws.com" in url


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
