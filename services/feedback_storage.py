"""Image storage for classifier feedback: Cloudflare R2, with a local fallback."""
import io
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st
from PIL import Image, ImageOps

try:
    import boto3
    from botocore.config import Config as BotoConfig
except ImportError:  # pragma: no cover - handled at runtime
    boto3 = None
    BotoConfig = None


logger = logging.getLogger(__name__)

LOCAL_STORAGE_DIR = Path("feedback_data/images")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_DIMENSION = 1024

R2_SECRET_KEYS = (
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
)


class StorageUploadError(RuntimeError):
    pass


def _get_secret(key: str) -> str:
    try:
        return st.secrets.get(key, "") or ""
    except Exception:
        return ""


def get_storage_backend() -> str:
    """Return 'r2' if R2 is fully configured, else 'local'."""
    configured = st.secrets.get("STORAGE_BACKEND", "") if _secrets_available() else ""
    if configured in ("r2", "local"):
        if configured == "r2" and not _r2_configured():
            logger.warning("STORAGE_BACKEND=r2 but R2 secrets are missing; falling back to local storage.")
            return "local"
        return configured
    return "r2" if _r2_configured() else "local"


def _secrets_available() -> bool:
    try:
        st.secrets.get("STORAGE_BACKEND", "")
        return True
    except Exception:
        return False


def _r2_configured() -> bool:
    return boto3 is not None and all(_get_secret(key) for key in R2_SECRET_KEYS)


@st.cache_resource
def _r2_client():
    if not _r2_configured():
        return None
    account_id = _get_secret("R2_ACCOUNT_ID")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=_get_secret("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_get_secret("R2_SECRET_ACCESS_KEY"),
        config=BotoConfig(signature_version="s3v4"),
        region_name="auto",
    )


def build_image_key(extension: str) -> str:
    now = datetime.now(timezone.utc)
    ext = extension.lstrip(".").lower() or "jpg"
    return f"feedback/{now:%Y}/{now:%m}/{uuid.uuid4().hex}.{ext}"


def prepare_image(raw_bytes: bytes) -> tuple[bytes, int, int, str]:
    """Downscale, strip EXIF, and normalize to JPEG. Returns (bytes, width, height, extension)."""
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise StorageUploadError("Image exceeds the 10 MB upload limit.")

    with Image.open(io.BytesIO(raw_bytes)) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")

        width, height = image.size
        longest_edge = max(width, height)
        if longest_edge > MAX_DIMENSION:
            scale = MAX_DIMENSION / longest_edge
            image = image.resize(
                (max(1, round(width * scale)), max(1, round(height * scale))),
                Image.LANCZOS,
            )

        clean = Image.new("RGB", image.size)
        clean.paste(image)

        buffer = io.BytesIO()
        clean.save(buffer, format="JPEG", quality=90)
        return buffer.getvalue(), clean.width, clean.height, "jpg"


def upload_image(image_bytes: bytes, image_key: str) -> None:
    backend = get_storage_backend()

    if backend == "r2":
        client = _r2_client()
        if client is None:
            raise StorageUploadError("R2 client is not configured.")
        client.put_object(
            Bucket=_get_secret("R2_BUCKET_NAME"),
            Key=image_key,
            Body=image_bytes,
            ContentType="image/jpeg",
        )
        return

    local_path = LOCAL_STORAGE_DIR / image_key.removeprefix("feedback/")
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(image_bytes)


def download_image(image_key: str) -> bytes:
    """Fetch a stored image's bytes, for the offline export script."""
    backend = get_storage_backend()

    if backend == "r2":
        client = _r2_client()
        if client is None:
            raise StorageUploadError("R2 client is not configured.")
        response = client.get_object(Bucket=_get_secret("R2_BUCKET_NAME"), Key=image_key)
        return response["Body"].read()

    local_path = LOCAL_STORAGE_DIR / image_key.removeprefix("feedback/")
    return local_path.read_bytes()


def store_feedback_image(raw_bytes: bytes) -> dict[str, Any]:
    """Prepare and upload an image, returning its key and dimensions.

    Raises StorageUploadError on bad/oversized input; upload failures are
    caught by the caller so feedback metadata can still be saved.
    """
    image_bytes, width, height, ext = prepare_image(raw_bytes)
    image_key = build_image_key(ext)
    upload_image(image_bytes, image_key)
    return {
        "image_key": image_key,
        "image_width": width,
        "image_height": height,
        "file_size_bytes": len(image_bytes),
    }
