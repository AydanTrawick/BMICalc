"""Neon Postgres persistence for classifier feedback (human-in-the-loop labels)."""
import logging
import time
from typing import Any

from psycopg import Error as PsycopgError
from psycopg.types.json import Jsonb

from services.auth_service import AuthConfigurationError, get_database_connection

logger = logging.getLogger(__name__)

VALID_VERDICTS = {"correct", "incorrect", "skipped"}


class FeedbackStoreError(RuntimeError):
    pass


def _with_retry(fn, *args, **kwargs):
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            return fn(*args, **kwargs)
        except (PsycopgError, AuthConfigurationError) as error:
            last_error = error
            logger.warning("classifier_feedback DB call failed (attempt %s): %s", attempt + 1, error)
            if attempt == 0:
                time.sleep(0.5)
    raise FeedbackStoreError(str(last_error)) from last_error


def find_existing_image_key(image_sha256: str) -> str | None:
    def _run():
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT image_key FROM classifier_feedback
                    WHERE image_sha256 = %s AND image_key IS NOT NULL
                    ORDER BY created_at ASC
                    LIMIT 1
                    """,
                    (image_sha256,),
                )
                row = cursor.fetchone()
                return row["image_key"] if row else None

    return _with_retry(_run)


def insert_feedback(record: dict[str, Any]) -> int:
    """Insert a classifier_feedback row. Returns the new row id."""
    verdict = record["user_verdict"]
    if verdict not in VALID_VERDICTS:
        raise ValueError(f"Invalid user_verdict: {verdict!r}")

    def _run():
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO classifier_feedback (
                        image_key, image_sha256, predicted_label, predicted_confidence,
                        top_k_predictions, user_verdict, corrected_label, final_label,
                        is_new_class, image_width, image_height, file_size_bytes, session_id
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    RETURNING id
                    """,
                    (
                        record.get("image_key"),
                        record["image_sha256"],
                        record["predicted_label"],
                        record["predicted_confidence"],
                        Jsonb(record.get("top_k_predictions")) if record.get("top_k_predictions") is not None else None,
                        verdict,
                        record.get("corrected_label"),
                        record.get("final_label"),
                        bool(record.get("is_new_class", False)),
                        record.get("image_width"),
                        record.get("image_height"),
                        record.get("file_size_bytes"),
                        record.get("session_id"),
                    ),
                )
                row = cursor.fetchone()
                return row["id"]

    return _with_retry(_run)


def get_summary_counts() -> dict[str, int]:
    def _run():
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT user_verdict, COUNT(*) AS count
                    FROM classifier_feedback
                    GROUP BY user_verdict
                    """
                )
                counts = {row["user_verdict"]: row["count"] for row in cursor.fetchall()}
                return {
                    "correct": counts.get("correct", 0),
                    "incorrect": counts.get("incorrect", 0),
                    "skipped": counts.get("skipped", 0),
                }

    return _with_retry(_run)


def get_confusion_table() -> list[dict[str, Any]]:
    def _run():
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT predicted_label, final_label, COUNT(*) AS count
                    FROM classifier_feedback
                    WHERE user_verdict = 'incorrect' AND final_label IS NOT NULL
                    GROUP BY predicted_label, final_label
                    ORDER BY count DESC
                    """
                )
                return list(cursor.fetchall())

    return _with_retry(_run)


def get_new_class_labels() -> list[dict[str, Any]]:
    def _run():
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT final_label, COUNT(*) AS count
                    FROM classifier_feedback
                    WHERE is_new_class = true AND final_label IS NOT NULL
                    GROUP BY final_label
                    ORDER BY count DESC
                    """
                )
                return list(cursor.fetchall())

    return _with_retry(_run)


def get_recent_records(limit: int = 25) -> list[dict[str, Any]]:
    def _run():
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, image_key, predicted_label, predicted_confidence,
                           user_verdict, corrected_label, final_label, is_new_class,
                           created_at
                    FROM classifier_feedback
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return list(cursor.fetchall())

    return _with_retry(_run)


def get_exportable_records() -> list[dict[str, Any]]:
    def _run():
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, image_key, final_label
                    FROM classifier_feedback
                    WHERE final_label IS NOT NULL
                      AND used_in_training = false
                      AND image_key IS NOT NULL
                    ORDER BY id ASC
                    """
                )
                return list(cursor.fetchall())

    return _with_retry(_run)


def mark_used_in_training(record_ids: list[int]) -> None:
    if not record_ids:
        return

    def _run():
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE classifier_feedback SET used_in_training = true WHERE id = ANY(%s)",
                    (record_ids,),
                )

    _with_retry(_run)


def update_record(record_id: int, final_label: str | None) -> None:
    def _run():
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE classifier_feedback SET final_label = %s WHERE id = %s",
                    (final_label, record_id),
                )

    _with_retry(_run)


def delete_record(record_id: int) -> None:
    def _run():
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM classifier_feedback WHERE id = %s",
                    (record_id,),
                )

    _with_retry(_run)
