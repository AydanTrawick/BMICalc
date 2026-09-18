"""Orchestrates classifier feedback: hashing, dedup, storage, and DB writes."""
import hashlib
import logging
from typing import Any

from services import feedback_storage as storage
from services import feedback_store as store
from services.feedback_labels import normalize_label

logger = logging.getLogger(__name__)


def sha256_of(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def resolve_final_label(verdict: str, predicted_label: str, corrected_label: str | None) -> str | None:
    if verdict == "correct":
        return predicted_label
    if verdict == "incorrect":
        return corrected_label
    if verdict == "skipped":
        return None
    raise ValueError(f"Unknown verdict: {verdict!r}")


def get_or_upload_image(raw_bytes: bytes, image_sha256: str) -> dict[str, Any]:
    """Reuse an existing R2/local key for this hash, or upload a new one.

    Returns a dict with image_key/image_width/image_height/file_size_bytes,
    all of which may be None if both dedup lookup and upload failed.
    """
    try:
        existing_key = store.find_existing_image_key(image_sha256)
    except store.FeedbackStoreError as error:
        logger.warning("Duplicate lookup failed, uploading as new: %s", error)
        existing_key = None

    if existing_key:
        try:
            _, width, height, _ = storage.prepare_image(raw_bytes)
        except storage.StorageUploadError:
            width = height = None
        return {
            "image_key": existing_key,
            "image_width": width,
            "image_height": height,
            "file_size_bytes": len(raw_bytes),
        }

    try:
        return storage.store_feedback_image(raw_bytes)
    except Exception as error:  # noqa: BLE001 - upload must never block feedback
        logger.error("Image upload failed, saving feedback without an image: %s", error)
        return {"image_key": None, "image_width": None, "image_height": None, "file_size_bytes": len(raw_bytes)}


def submit_feedback(
    *,
    raw_bytes: bytes,
    predicted_label: str,
    predicted_confidence: float,
    top_k_predictions: list[dict[str, Any]] | None,
    verdict: str,
    class_names: list[str],
    session_id: str,
    corrected_label_raw: str | None = None,
) -> dict[str, Any]:
    """Build and persist a feedback record. Returns {id, final_label, is_new_class}."""
    corrected_label = None
    is_new_class = False

    if verdict == "incorrect":
        if not corrected_label_raw or not corrected_label_raw.strip():
            raise ValueError("A corrected label is required when the prediction is marked incorrect.")
        corrected_label = normalize_label(corrected_label_raw)
        known = {normalize_label(name) for name in class_names}
        is_new_class = corrected_label not in known

    final_label = resolve_final_label(verdict, predicted_label, corrected_label)

    image_sha256 = sha256_of(raw_bytes)
    image_info = get_or_upload_image(raw_bytes, image_sha256)

    record_id = store.insert_feedback(
        {
            "image_key": image_info.get("image_key"),
            "image_sha256": image_sha256,
            "predicted_label": predicted_label,
            "predicted_confidence": predicted_confidence,
            "top_k_predictions": top_k_predictions,
            "user_verdict": verdict,
            "corrected_label": corrected_label,
            "final_label": final_label,
            "is_new_class": is_new_class,
            "image_width": image_info.get("image_width"),
            "image_height": image_info.get("image_height"),
            "file_size_bytes": image_info.get("file_size_bytes"),
            "session_id": session_id,
        }
    )

    return {"id": record_id, "final_label": final_label, "is_new_class": is_new_class}
