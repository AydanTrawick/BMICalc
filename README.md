# FirstRep Toolkit

Run locally:

```sh
python3 -m pip install -r requirements.txt
python3 -m streamlit run BMI2.py
```

The BMI calculator records adult readings with metric or imperial inputs, a band marker, and history. The Workout Log tracks exercises, effort, notes, and derived volume. The Food Log supports USDA FoodData Central search, common foods, or manual macros and derives calories using 4/4/9.

Signed-in users' BMI, workout, and food logs are saved in Neon. Each log loads when first opened after login; **Reload saved log** fetches changes from another browser. Additions, edits, and deletions are committed before a successful save is shown. Edits detect conflicting changes from other sessions, and retrying a failed save uses the same entry IDs to avoid duplicates.

Guests can still use all three trackers, but guest entries last only for the browser session. After signing in, use **Add guest entries to my account** on each log to import those entries explicitly. Signing out clears private session data. CSV downloads remain available as optional backups. CSV restore replaces only the signed-in user's selected log after validation and confirmation; it does not affect other users.

Workout and food tables support editing and deletion, as does BMI history. Save edits to recalculate totals. Weights in the editor and CSV files use kilograms; BMI timestamps use UTC. No calorie targets are generated.

Common foods can be entered in grams, ounces, or pounds; mass units are converted to grams before macros are calculated. USDA foods also offer household measures and serving sizes when FoodData Central supplies a gram weight for them. Manual entry uses macros for the whole portion eaten. Food calories use the simplified 4/4/9 calculation and can differ from package labels.

Account, store, email, and chat features use their existing Streamlit secrets configuration. The trackers can be used without accounts. Run [database/001_create_tracker_tables.sql](database/001_create_tracker_tables.sql) once if the tables are not already installed; see [setup instructions](database/README.md). Configure `NEON_DATABASE_URL` in local and hosted Streamlit secrets. Existing installed tables require no additional migration for persistence.

Run checks:

```sh
python3 -m unittest discover -s tests -v
```

Live integration checks (requires the configured Neon database):

```sh
FIRSTREP_RUN_NEON_TESTS=1 python3 -m unittest discover -s tests -v
```

Live tests create unique temporary accounts, exercise saving and reloading across logins, edits, deletion, CSV restore, account separation, rollback, and retries, then delete those test accounts and their logs. Ordinary tests do not create accounts in Neon.

## USDA food search setup

Obtain a key from [USDA FoodData Central](https://fdc.nal.usda.gov/api-key-signup/). Add this **top-level** setting to `.streamlit/secrets.toml` (before any TOML section headers), or to your hosted app’s Streamlit secrets:

```toml
USDA_API_KEY = "your-usda-api-key"
```

Alternatively, set the server environment variable `USDA_API_KEY`. Restart the app after configuration. Keep the key on the server; `.streamlit/secrets.toml` is gitignored. No database migration is needed. Install the current requirements, including `certifi` for verified HTTPS connections. A placeholder is provided in `.streamlit/secrets.toml.example`; merge the setting into your existing secrets rather than replacing them.

In **Food log → USDA food search**, search by food or brand, browse results, select a food, enter the amount in grams, review the portion macros, choose the date, and press **Add to food log**. The selected food, brand, USDA ID, amount, and scaled macros use the existing guest/account log storage and daily totals. Calories retain the app’s 4/4/9 calculation. Foods missing any required macro cannot be added through search; use another result or manual label entry. Search and detail responses are cached briefly to reduce API requests.

The integration uses the official [FoodData Central search and detail endpoints](https://fdc.nal.usda.gov/api-guide/). The glossary is available as a separate page from Home and the tracker guide links.

## Staying signed in

Login and account creation now keep this browser signed in for seven days, including page refreshes and reopening the app. After updating, sign in once to create the browser session. Log out on shared devices. Logout revokes that browser’s token before clearing private session data. Existing tabs recheck the session on interaction at most once per minute; expired or revoked sessions must sign in again.

The app automatically creates `firstrep_login_sessions` in the existing Neon database on first login; no additional secret is needed. It stores only SHA-256 hashes of random session tokens, with an enforced expiry and a foreign key to the account. Deleted accounts lose their sessions. Roles are loaded from the database. Expired rows are cleaned up at login.

The browser stores an opaque token in a host-only `SameSite=Lax` cookie, marked `Secure` on HTTPS. Deploy over HTTPS. Streamlit’s component writes the cookie with JavaScript, so it cannot be `HttpOnly`; keep untrusted scripts out of the app. Passwords and account details are never written to the cookie or URL. Requires Streamlit 1.58 or newer. If cookies are blocked, login lasts only for the current connection.

## Appearance

The app uses the same dark palette for system, light, and dark selections. `.streamlit/config.toml` controls Streamlit surfaces, inputs, tables, and sidebar colors; custom cards and chat styles use the same dark appearance regardless of the operating system’s theme. Restart the server after updating the app configuration.

USDA HTTPS requests retain certificate verification and load the `certifi` CA bundle in addition to system trust roots, including on macOS Python installations without a default certificate bundle.

## Voice and text AI Plan Builder

Open **AI Plan Builder** from Home or the sidebar. Install `requirements.txt`, then merge these top-level values into `.streamlit/secrets.toml` (or hosted Streamlit secrets) and restart the app:

```toml
OPENAI_API_KEY = "your-openai-api-key"
ANTHROPIC_API_KEY = "your-anthropic-api-key"
```

Use `.streamlit/secrets.toml.example` as a reference; do not replace existing database or other keys. The real secrets file is gitignored. Python 3.10+ is required. The app already requires Streamlit 1.58+, which includes `st.audio_input`.

Type a meal or workout request, or record up to 60 seconds and press **Transcribe recording**. Voice uses OpenAI `whisper-1`; review and edit the transcript before sending it. Claude `claude-sonnet-5` extracts requirements and generates plans. Typed input needs only the Anthropic key. The provider accounts must have access to these models. Audio is sent to OpenAI only when transcribed; submitted text, requirements, and any current plan are sent to Anthropic. Avoid including identifying health information.

The builder asks one combined question for missing details, with at most two clarification rounds per build or edit. Defaults are then listed in the plan notes; unanswered injury status remains explicitly unknown. Requests below 1,200 calories/day are raised to that floor with an explanation; the floor is not a personalized recommendation. Workout injuries and health conditions always receive a professional-review note.

Pydantic checks structure; Python checks counts, food exclusions, required ingredients, calories, workout volume, duration, and common injury conflicts. Required foods must appear **at least once across the whole plan**. Grocery quantities are combined from actual recipes. Conservative keyword matching can flag substitutes such as gluten-free bread or dairy-free yogurt; checks are not a guarantee of allergen safety. Injury checks cover common movement conflicts and do not establish medical suitability.

Invalid JSON is retried once, provider failures once, and rule failures receive up to two repair attempts. Plans that still break exclusions or the calorie floor are hidden and cannot be exported. Other unresolved checks appear prominently in the page and downloads. Larger plans are generated a day at a time to stay within a 6,000-token response budget, so one plan can require several provider calls.

Ask for edits such as “swap day 2 lunch for something with rice” or “make it 5 days.” Earlier restrictions are retained; **Start over** is required to remove a food exclusion. View days in tabs and download Markdown or plain text, including notes and disclaimers. PDF export is not included. Plans are session-only and are not saved to the account database. Start over clears only builder data, preserving login and trackers. The limit is 10 builds/edits per Streamlit session, including failed generation attempts; Start over does not reset that counter. Clarification alone does not consume a build. Reloading creates a new Streamlit session, so this is not an account-level billing limit.

Identical recordings are reused only within the current session; health-related requests and plans are not placed in a shared cache. A generated plan is reused on ordinary Streamlit reruns without another API call.

## Floating Training Assistant

The circular microphone button on every page opens **Training Assistant**. This replaces the older floating text coach. It uses a uniquely keyed Streamlit button (`training_assistant_launcher`) with fixed-position CSS, a large `st.dialog`, and a nested `st.fragment`. Normal chat interactions rerun only that fragment. The rest of the page stays usable after closing the dialog; the mobile button includes bottom safe-area spacing.

Install the updated requirements and merge these top-level secrets from `.streamlit/secrets.toml.example`:

```toml
ANTHROPIC_API_KEY = "your-anthropic-api-key"
OPENAI_API_KEY = "your-openai-api-key"
ELEVENLABS_API_KEY = "your-elevenlabs-api-key"
ELEVENLABS_VOICE_ID = "your-elevenlabs-voice-id"
NEON_DATABASE_URL = "postgresql://user:password@host/database?sslmode=require"
ASSISTANT_TIMEZONE = "America/New_York"
```

Restart Streamlit after configuring secrets. `.streamlit/secrets.toml` remains gitignored. The assistant reuses the existing Anthropic client, `claude-sonnet-5`, secrets reader, and 60-second `whisper-1` transcription implementation. Voice recording needs browser microphone permission and HTTPS or localhost. A completed recording is transcribed once; the input key changes even if transcription fails. Review the parsed fields before confirming a write. Typed chat needs no OpenAI key.

ElevenLabs uses `eleven_turbo_v2_5` and the configured voice. **Speak replies** defaults on and persists while navigating. Only the first two sentences (at most 300 characters) are spoken; an overlong first sentence gets a brief “read the chat” message. Confirmation cards are never spoken. TTS is cached for one hour by text hash, user scope, voice, and credential hash; one user's health-related audio is not shared with another. Browser autoplay rules may require pressing Play. Missing configuration, quota errors, and network failures leave the text reply usable.

The assistant uses the existing signed-in user's ID, never a user ID supplied by Claude or an editable form. Guests can ask general questions; saved-data tools require sign-in. It uses exactly your existing `activity_logs`, `assistant_messages`, and `user_plans` tables. **No assistant table is created from Python and no migration is run.** The pre-existing account system retains its own setup behavior. Activity reads exclude soft-deleted rows; messages and plans have no `deleted_at` column, so their reads use owner and conversation/active-plan filters instead. Database access uses a locked, cached psycopg connection, required SSL, a 10-second connect timeout, and one connection retry. All SQL values are parameters.

Claude can read history and progress immediately. Logging strength, cardio, meals, bodyweight, deleting an entry, or editing a plan produces a preview with **Confirm**, **Edit**, and **Cancel**. Multiple proposed changes require separate confirmations. Editing returns to a new preview; it never saves directly. Missing duration, pace, RPE, calories, and protein remain null. Weights require an explicit unit. Date phrases are resolved in Python, with US month/day interpretation for `9/15`; “last Monday” means the previous Monday, even on Monday. Last week means Monday–Sunday, and this month ends today. Dates outside the past calendar year or in the future are rejected.

Confirmed writes create transactionally committed operation receipts in `assistant_messages.tool_calls`. Repeating the same confirmation after an uncertain response returns its existing result instead of inserting a duplicate. Once a save was attempted, editing is locked until it is reconciled. Cancel checks its receipt before claiming no change occurred. **Undo** stages a confirmation: new activity entries are soft-deleted, deletion can be reversed, and plan changes restore the previous snapshot. Active-plan edits use optimistic checks so an old preview cannot overwrite a newer version. Undo state survives page navigation in the session; saved receipts survive reconnections.

Assistant entries appear under **Assistant activity log** on the Workout Log and Food Log pages. These new tables are deliberately separate from the earlier manual trackers: their entries are not copied into legacy tables, and existing Home/manual tracker totals are unchanged. Assistant history and progress currently summarize `activity_logs` only, and replies identify that coverage. Volume converts pounds to kilograms; timed/ranged reps or unknown weights are excluded and counted as incomplete. Training sessions mean distinct date/type pairs, streaks count training days, and PRs compare weight at equal rep counts against earlier active records. First observations establish baselines. Bodyweight change needs at least two measurements. Distances are normalized to kilometers and broken down by activity.

The AI Plan Builder remains separate. After generating a valid Builder plan, open the assistant and choose **Save Builder plan as active copy**, then confirm. The saved `plan_data` contains `{ "plan": <MealPlan or WorkoutPlan>, "request": <PlanRequest> }`, retaining exclusions, equipment, and other constraints. Saved plan edits change exactly one meal or exercise, regenerate appropriate instructions/form cues, and run the existing validation rules before a preview can be confirmed. Other days remain unchanged. A weekday such as Wednesday needs a known mapping to a numbered training day; the assistant asks when ambiguous. Raw externally saved plans without requirements can be read, but must be replaced with a validated Builder copy before automatic edits. The Builder draft itself is never changed by assistant edits. **Saved active plans → Load saved plans** shows the saved copy.

Conversation history loads the last 20 saved messages and stays in session while navigating. Clear conversation adds a history marker; it does not hard-delete the audit history or reset the 30-request session limit. Each request has at most five tool-loop steps and a 2,000-token reply budget. Confirmation continuations remain available at the cap. The limit is per Streamlit session, not an account billing quota. Plan replacement previews may use an additional bounded generation call per proposed item. Do not include identifying information you do not want sent to the providers: speech is sent to OpenAI, submitted text and requested tool results to Anthropic, and short spoken replies to ElevenLabs.

To add a tool, define a Pydantic argument model and description in `assistant/tools.py`, route it in `assistant/executor.py`, and add tests. Mutating tools must be in `WRITE_TOOLS`, return a `PendingAction`, use the authenticated identity and parameterized SQL, and return an ID plus an undo receipt. Never expose raw SQL or a user ID argument to the model.

Run all offline checks with `python3 -m pytest tests -q`. The opt-in integration below uses the **existing** Neon tables in a forced-rollback transaction; it verifies ownership, null duration, idempotency, soft deletion, conversation reset, plan changes, and undo. It leaves no test rows and changes no schema (Postgres sequence counters may advance):

```sh
FIRSTREP_RUN_ASSISTANT_DB_TESTS=1 python3 -m pytest tests/test_assistant_neon.py -q
```

Manual checks: propose a three-mile run and confirm; log a bench press and supply its unit when asked; query legs last week and progress this month; ask a general soreness question; use Undo; save a Builder plan and request a single exercise replacement; navigate away and reopen the dialog; switch speech off and verify replies remain text-only.

Run all tests (provider calls are mocked; live database tests remain opt-in):

```sh
python3 -m pytest tests -q
```

## Equipment Classifier feedback loop

The Equipment Classifier page calls a separate FastAPI service (`equipment_api/`) that runs the trained ResNet18 model; the Streamlit app never touches the model directly. After every prediction, the page asks **Is this correct?** and turns the answer into a growing, human-verified labeled dataset for retraining:

- **Yes, correct** saves the image with `user_verdict='correct'` and `final_label` set to the model's prediction.
- **No, it's something else** shows a dropdown of the model's known classes plus a free-text fallback (with a fuzzy-match "Did you mean…" suggestion via `difflib`), saves `user_verdict='incorrect'`, and sets `final_label` to the corrected label. A corrected label outside the known class list is flagged `is_new_class=true`.
- **Not sure / skip** saves `user_verdict='skipped'` with no `final_label`, for later manual review.

Images are uploaded to Cloudflare R2 (`services/feedback_storage.py`) after being downscaled to at most 1024px on the long edge, stripped of EXIF metadata, and capped at 10 MB; a local `./feedback_data/images/` fallback is used automatically when R2 secrets are absent (`STORAGE_BACKEND` can also force one backend). Metadata is written to the `classifier_feedback` table in Neon (`services/feedback_store.py`); see [database/README.md](database/README.md) for the migration. The same uploaded image submitted twice reuses one stored file but always records a separate feedback row (`services/feedback_logic.py`, deduped by SHA-256). If either storage backend or the database is unreachable, classification and feedback submission still succeed — errors are logged, not surfaced to the user.

**Review the collected feedback** on `pages/Feedback_Review.py`, gated behind `ADMIN_PASSWORD` in Streamlit secrets (separate from the account-based admin pages). It shows verdict counts, accuracy (`correct / (correct + incorrect)`), a confusion table of predicted vs. corrected labels, candidate new classes, recent records with inline edit/delete, and a CSV export button.

**Retrain on the collected data**: run `python scripts/export_training_data.py [--mark-used] [--min-count N]` to download every row with a `final_label` into `training_export/<label>/` (an `ImageFolder`-compatible layout for torchvision), skipping classes below `--min-count` and warning about classes under 20 examples. Pass `--mark-used` to set `used_in_training=true` on exported rows so a later export doesn't repeat them.

**Adding a new class to the model**: check the Feedback Review page's "Candidate new classes" table for corrected labels with enough examples, add the label to `CLASS_NAMES` in both `equipment_api/equipment_api.py` and `services/equipment_classes.py` (the two must stay in sync — they run as separate services), retrain and redeploy `best_equipment_model.pth`, then use the export script to pull training images for the new class.
