-- FirstRep: run this entire file in the Neon SQL Editor for the database
-- used by NEON_DATABASE_URL. Existing tables and rows are preserved.
-- services/feedback_store.py reads and writes this table for the
-- Equipment Classifier's human-in-the-loop feedback flow.
BEGIN;

CREATE TABLE IF NOT EXISTS public.classifier_feedback (
    id BIGSERIAL PRIMARY KEY,
    image_key TEXT,
    image_sha256 TEXT NOT NULL,
    predicted_label TEXT NOT NULL,
    predicted_confidence REAL NOT NULL,
    top_k_predictions JSONB,
    user_verdict TEXT NOT NULL CHECK (user_verdict IN ('correct', 'incorrect', 'skipped')),
    corrected_label TEXT,
    final_label TEXT,
    is_new_class BOOLEAN NOT NULL DEFAULT false,
    image_width INT,
    image_height INT,
    file_size_bytes INT,
    session_id TEXT,
    used_in_training BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- If this table was already created with `image_key TEXT NOT NULL UNIQUE`,
-- relax it: multiple feedback rows may legitimately share one image_key
-- when several people give feedback on the same uploaded image (see
-- services/feedback_logic.get_or_upload_image, which reuses the key by
-- sha256 instead of re-uploading the file).
ALTER TABLE public.classifier_feedback ALTER COLUMN image_key DROP NOT NULL;
ALTER TABLE public.classifier_feedback DROP CONSTRAINT IF EXISTS classifier_feedback_image_key_key;

CREATE INDEX IF NOT EXISTS classifier_feedback_sha256_idx
    ON public.classifier_feedback (image_sha256);
CREATE INDEX IF NOT EXISTS classifier_feedback_final_label_idx
    ON public.classifier_feedback (final_label)
    WHERE final_label IS NOT NULL AND used_in_training = false;
CREATE INDEX IF NOT EXISTS classifier_feedback_verdict_idx
    ON public.classifier_feedback (user_verdict);

-- This table stores no personal identity: session_id is a random per-session
-- UUID, not an account ID or IP address. Images are uploaded gym-equipment
-- photos; the app asks users not to upload photos of people.
COMMIT;
