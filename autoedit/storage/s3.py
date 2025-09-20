from __future__ import annotations

from pathlib import Path
from typing import Optional

try:
    import boto3
    from botocore.client import Config as BotoConfig
except Exception as exc:  # pragma: no cover - dependency missing
    raise ImportError(
        "boto3 is required for S3 storage. Install with 'pip install boto3' or use the "
        "[storage] extra."
    ) from exc

from .base import StorageClient, UploadResult


class S3StorageClient(StorageClient):
    def __init__(
        self,
        *,
        bucket: str | None,
        prefix: Optional[str] = None,
        region: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        session_token: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        expiration: int = 3600,
    ) -> None:
        if not bucket:
            raise ValueError("S3 bucket is required for uploads")
        self.bucket = bucket
        self.prefix = prefix.rstrip("/") if prefix else None
        self.expiration = expiration

        kwargs: dict = {}
        if region:
            kwargs["region_name"] = region
        if access_key and secret_key:
            kwargs["aws_access_key_id"] = access_key
            kwargs["aws_secret_access_key"] = secret_key
        if session_token:
            kwargs["aws_session_token"] = session_token
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url

        self._client = boto3.client("s3", config=BotoConfig(signature_version="s3v4"), **kwargs)

    def upload_file(self, local_path: Path, *, target_name: Optional[str] = None) -> UploadResult:
        key = target_name or local_path.name
        if self.prefix:
            key = f"{self.prefix}/{key}"
        self._client.upload_file(str(local_path), self.bucket, key)
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=self.expiration,
        )
        return UploadResult(url=url, key=key)
