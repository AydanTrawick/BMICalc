import hashlib
import io
from unittest.mock import Mock, patch

import pytest
from PIL import Image
from PIL.ExifTags import Base as ExifBase

from services import feedback_labels, feedback_logic, feedback_storage, feedback_store


CLASS_NAMES = ["Lat Pulldown", "Bench Press", "Squat"]


def make_jpeg_bytes(size=(50, 50), with_gps=False) -> bytes:
    image = Image.new("RGB", size, color=(120, 60, 30))
    buffer = io.BytesIO()
    if with_gps:
        exif = image.getexif()
        exif[ExifBase.Make.value] = "TestCam"
        gps_ifd = exif.get_ifd(ExifBase.GPSInfo.value)
        gps_ifd[1] = "N"
        gps_ifd[2] = (37.0, 46.0, 0.0)
        image.save(buffer, format="JPEG", exif=exif)
    else:
        image.save(buffer, format="JPEG")
    return buffer.getvalue()


# --- label normalization -------------------------------------------------

def test_normalize_label_strips_lowercases_and_collapses_spaces():
    assert feedback_labels.normalize_label("  Lat   PullDown  ") == "lat pulldown"


def test_normalize_label_strips_trailing_punctuation():
    assert feedback_labels.normalize_label("leg press.") == "leg press"


def test_normalize_label_rejects_empty():
    with pytest.raises(feedback_labels.InvalidLabelError):
        feedback_labels.normalize_label("   ")


def test_normalize_label_rejects_too_long():
    with pytest.raises(feedback_labels.InvalidLabelError):
        feedback_labels.normalize_label("x" * 61)


# --- fuzzy matching --------------------------------------------------------

def test_fuzzy_match_suggests_known_class():
    suggestion = feedback_labels.suggest_close_match("lat pull down", CLASS_NAMES)
    assert suggestion == "Lat Pulldown"


def test_fuzzy_match_returns_none_when_no_close_class():
    assert feedback_labels.suggest_close_match("rowing machine", CLASS_NAMES) is None


# --- final_label resolution -------------------------------------------------

def test_final_label_correct_uses_predicted_label():
    assert feedback_logic.resolve_final_label("correct", "Squat", None) == "Squat"


def test_final_label_incorrect_uses_corrected_label():
    assert feedback_logic.resolve_final_label("incorrect", "Squat", "bench press") == "bench press"


def test_final_label_skipped_is_none():
    assert feedback_logic.resolve_final_label("skipped", "Squat", None) is None


# --- is_new_class via submit_feedback --------------------------------------

def test_submit_feedback_flags_unknown_corrected_label_as_new_class():
    raw_bytes = make_jpeg_bytes()
    with patch.object(feedback_logic, "get_or_upload_image", return_value={
        "image_key": "feedback/2026/01/abc.jpg", "image_width": 50, "image_height": 50, "file_size_bytes": 100,
    }), patch.object(feedback_store, "insert_feedback", return_value=42) as insert:
        result = feedback_logic.submit_feedback(
            raw_bytes=raw_bytes,
            predicted_label="Squat",
            predicted_confidence=0.4,
            top_k_predictions=None,
            verdict="incorrect",
            class_names=CLASS_NAMES,
            session_id="session-1",
            corrected_label_raw="leg press machine",
        )
    assert result["is_new_class"] is True
    assert result["final_label"] == "leg press machine"
    assert insert.call_args.args[0]["is_new_class"] is True


def test_submit_feedback_known_corrected_label_is_not_new_class():
    raw_bytes = make_jpeg_bytes()
    with patch.object(feedback_logic, "get_or_upload_image", return_value={
        "image_key": "feedback/2026/01/abc.jpg", "image_width": 50, "image_height": 50, "file_size_bytes": 100,
    }), patch.object(feedback_store, "insert_feedback", return_value=1):
        result = feedback_logic.submit_feedback(
            raw_bytes=raw_bytes,
            predicted_label="Squat",
            predicted_confidence=0.9,
            top_k_predictions=None,
            verdict="incorrect",
            class_names=CLASS_NAMES,
            session_id="session-1",
            corrected_label_raw="Bench Press",
        )
    assert result["is_new_class"] is False
    assert result["final_label"] == "bench press"


def test_submit_feedback_requires_corrected_label_when_incorrect():
    with pytest.raises(ValueError):
        feedback_logic.submit_feedback(
            raw_bytes=make_jpeg_bytes(),
            predicted_label="Squat",
            predicted_confidence=0.9,
            top_k_predictions=None,
            verdict="incorrect",
            class_names=CLASS_NAMES,
            session_id="session-1",
            corrected_label_raw="   ",
        )


# --- duplicate detection ----------------------------------------------------

def test_duplicate_image_reuses_existing_key_without_reuploading():
    raw_bytes = make_jpeg_bytes()
    with patch.object(feedback_store, "find_existing_image_key", return_value="feedback/2026/01/existing.jpg") as find, \
         patch.object(feedback_storage, "store_feedback_image") as upload:
        result = feedback_logic.get_or_upload_image(raw_bytes, feedback_logic.sha256_of(raw_bytes))
    find.assert_called_once()
    upload.assert_not_called()
    assert result["image_key"] == "feedback/2026/01/existing.jpg"


def test_new_image_uploads_when_no_existing_hash():
    raw_bytes = make_jpeg_bytes()
    with patch.object(feedback_store, "find_existing_image_key", return_value=None), \
         patch.object(feedback_storage, "store_feedback_image", return_value={
             "image_key": "feedback/2026/01/new.jpg", "image_width": 50, "image_height": 50, "file_size_bytes": 100,
         }) as upload:
        result = feedback_logic.get_or_upload_image(raw_bytes, feedback_logic.sha256_of(raw_bytes))
    upload.assert_called_once()
    assert result["image_key"] == "feedback/2026/01/new.jpg"


def test_sha256_is_stable_for_same_bytes():
    raw_bytes = make_jpeg_bytes()
    assert feedback_logic.sha256_of(raw_bytes) == hashlib.sha256(raw_bytes).hexdigest()


# --- EXIF stripping and downscaling -----------------------------------------

def test_prepare_image_strips_exif_gps_data():
    raw_bytes = make_jpeg_bytes(with_gps=True)
    cleaned_bytes, width, height, ext = feedback_storage.prepare_image(raw_bytes)
    with Image.open(io.BytesIO(cleaned_bytes)) as cleaned:
        assert cleaned.getexif() == {}
    assert ext == "jpg"


def test_prepare_image_downscales_large_images():
    raw_bytes = make_jpeg_bytes(size=(2000, 1000))
    cleaned_bytes, width, height, _ = feedback_storage.prepare_image(raw_bytes)
    assert width == feedback_storage.MAX_DIMENSION
    assert height == 512


def test_prepare_image_rejects_oversized_upload():
    with patch.object(feedback_storage, "MAX_UPLOAD_BYTES", 10):
        with pytest.raises(feedback_storage.StorageUploadError):
            feedback_storage.prepare_image(make_jpeg_bytes())


# --- storage backend selection ----------------------------------------------

def test_local_backend_used_when_r2_not_configured():
    with patch.object(feedback_storage, "_r2_configured", return_value=False), \
         patch.object(feedback_storage, "_secrets_available", return_value=False):
        assert feedback_storage.get_storage_backend() == "local"


def test_upload_image_writes_to_local_path_for_local_backend(tmp_path):
    with patch.object(feedback_storage, "get_storage_backend", return_value="local"), \
         patch.object(feedback_storage, "LOCAL_STORAGE_DIR", tmp_path):
        feedback_storage.upload_image(b"fake-bytes", "feedback/2026/01/abc.jpg")
    assert (tmp_path / "2026/01/abc.jpg").read_bytes() == b"fake-bytes"
