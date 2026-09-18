# Create the tracking tables in Neon

1. Open your Neon project and its **SQL Editor**.
2. Select the branch and database used by the app's `NEON_DATABASE_URL`.
3. Paste the entire contents of [001_create_tracker_tables.sql](001_create_tracker_tables.sql) and run it.
4. Confirm the tables exist:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'firstrep_users',
    'firstrep_bmi_readings',
    'firstrep_workout_entries',
    'firstrep_food_entries'
  )
ORDER BY table_name;
```

The migration runs in one transaction. It creates the user table if needed, matches the existing account code, and leaves existing users intact. Re-running the same migration does not duplicate tables or delete records. `IF NOT EXISTS` does not upgrade a differently defined existing tracker table; future changes need another migration.

| Table | Stores |
| --- | --- |
| `firstrep_users` | Existing account fields, password hashes and salts, and roles |
| `firstrep_bmi_readings` | User, timestamp, height in cm, and weight in kg |
| `firstrep_workout_entries` | User, date, exercise, sets, reps, weight in kg, RPE, and notes |
| `firstrep_food_entries` | User, date, food description, and grams of each macro |

Each log entry has a stable UUID and a required foreign key to an existing account. Deleting an account deletes its associated tracking entries. New workouts use one row per set, so weights can differ between sets; the `sets` field also accepts existing grouped CSV records. BMI, calories, and volume remain derived from their inputs.

## Application integration

The app now uses these tables through `services/tracking_store.py` and the existing authenticated user ID. No further migration is required if these tables are already installed.

- Signed-in users save and load account-owned entries; every database read, update, and deletion includes the user ID.
- Logging out clears private session data. Guest entries can be explicitly imported after login.
- Multi-set saves and log edits/imports run in transactions. Successful saves are shown only after commit; failed saves keep input available for retry.
- Stable entry IDs support edits/deletion and prevent duplicate retries. Edits compare the original snapshot to the database and reject conflicting changes from another browser.
- Account-row locks serialize writes for one user. Independent accounts are not locked together.
- **Reload saved log** refreshes data from another session. CSV downloads are optional backups for signed-in users.

Keep `NEON_DATABASE_URL` in Streamlit secrets, including the hosted app's secrets. Neon's pooled connection is supported. The database connection uses bounded connection, statement, and lock timeouts. Do not put credentials in SQL files or browser code.

Neon SQL Editor documentation: https://neon.com/docs/get-started/signing-up

## classifier_feedback

Run [002_create_classifier_feedback_table.sql](002_create_classifier_feedback_table.sql) the same way to add the Equipment Classifier's human-in-the-loop feedback table. It also relaxes `image_key` from `NOT NULL UNIQUE` if an earlier version of the table had that constraint: multiple feedback rows can legitimately share one `image_key` when the same uploaded image gets more than one round of feedback (see `services/feedback_logic.get_or_upload_image`). `services/feedback_store.py` reads and writes this table; `services/feedback_storage.py` handles the actual image bytes (Cloudflare R2, or `./feedback_data/images/` locally when R2 secrets are absent).
