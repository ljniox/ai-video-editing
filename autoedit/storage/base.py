from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class UploadResult:
    url: str
    key: Optional[str] = None


class StorageClient(ABC):
    """Abstract storage interface for uploading artifacts."""

    @abstractmethod
    def upload_file(self, local_path: Path, *, target_name: Optional[str] = None) -> UploadResult:
        """Upload the given file and return an accessible URL."""


def load_storage_client(config: dict | None) -> Optional[StorageClient]:
    if not config:
        return None
    provider = str(config.get("provider") or "local").lower()
    if provider == "local":
        return None
    if provider == "s3":
        from .s3 import S3StorageClient

        return S3StorageClient(
            bucket=config.get("bucket"),
            prefix=config.get("prefix"),
            region=config.get("region"),
            access_key=config.get("access_key"),
            secret_key=config.get("secret_key"),
            session_token=config.get("session_token"),
            endpoint_url=config.get("endpoint_url"),
            expiration=int(config.get("presign_expiration", 3600)),
        )
    raise ValueError(f"Unsupported storage provider: {provider}")
