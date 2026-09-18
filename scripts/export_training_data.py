"""Export labeled classifier feedback into an ImageFolder-compatible directory.

Run manually (not from the Streamlit app):

    python scripts/export_training_data.py [--mark-used] [--min-count N]

Requires the same secrets as the app (NEON_DATABASE_URL and, for R2-backed
deployments, the R2_* keys) in .streamlit/secrets.toml or the environment.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.feedback_storage import StorageUploadError, download_image  # noqa: E402
from services.feedback_store import (  # noqa: E402
    FeedbackStoreError,
    get_exportable_records,
    mark_used_in_training,
)

OUTPUT_DIR = Path("training_export")
MIN_COUNT_WARNING_DEFAULT = 20


def slugify_label(label: str) -> str:
    return "".join(char if char.isalnum() or char in "-_ " else "_" for char in label).strip().replace(" ", "_")


def export(mark_used: bool, min_count: int) -> None:
    try:
        records = get_exportable_records()
    except FeedbackStoreError as error:
        print(f"Could not load exportable records: {error}")
        raise SystemExit(1)

    if not records:
        print("No exportable records found (final_label set, not yet used in training).")
        return

    label_counts = Counter(record["final_label"] for record in records)
    skipped_labels = {label for label, count in label_counts.items() if count < min_count}

    OUTPUT_DIR.mkdir(exist_ok=True)

    exported_ids: list[int] = []
    downloaded = 0
    failed = 0

    for record in records:
        label = record["final_label"]
        if label in skipped_labels:
            continue

        label_dir = OUTPUT_DIR / slugify_label(label)
        label_dir.mkdir(parents=True, exist_ok=True)

        filename = Path(record["image_key"]).name
        destination = label_dir / f"{record['id']}_{filename}"

        try:
            image_bytes = download_image(record["image_key"])
        except (StorageUploadError, OSError) as error:
            print(f"  ! Failed to download {record['image_key']}: {error}")
            failed += 1
            continue

        destination.write_bytes(image_bytes)
        downloaded += 1
        exported_ids.append(record["id"])

    print(f"\nExported {downloaded} image(s) to {OUTPUT_DIR}/ ({failed} failed).")

    print("\nClass distribution:")
    for label, count in sorted(label_counts.items(), key=lambda item: -item[1]):
        flag = "  [SKIPPED: below --min-count]" if label in skipped_labels else ""
        warn = "  ⚠ fewer than 20 examples" if count < MIN_COUNT_WARNING_DEFAULT else ""
        print(f"  {label}: {count}{flag}{warn}")

    if mark_used and exported_ids:
        mark_used_in_training(exported_ids)
        print(f"\nMarked {len(exported_ids)} record(s) as used_in_training.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mark-used", action="store_true", help="Set used_in_training=true on exported rows.")
    parser.add_argument("--min-count", type=int, default=1, help="Skip classes with fewer than N examples.")
    args = parser.parse_args()

    export(mark_used=args.mark_used, min_count=args.min_count)


if __name__ == "__main__":
    main()
