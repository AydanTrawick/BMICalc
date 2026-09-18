"""Validated input records; calculated fields are always derived."""
import math
import io
from datetime import date, datetime, timezone

import pandas as pd
import streamlit as st

from uuid import uuid4
from services import tracking_store as storage
from services.tracking_store import SCHEMAS, StorageError


def change_user(user):
    """Clear private session state at the authentication boundary."""
    old_user = st.session_state.get('firstrep_user')
    guest = {kind: st.session_state.get(kind, []) for kind in SCHEMAS} if not old_user and user else {}
    st.session_state.clear()
    if user:
        st.session_state['firstrep_user'] = user
        st.session_state['_guest_logs'] = guest
    st.session_state['_tracking_owner'] = user['id'] if user else None


def owner():
    return (st.session_state.get('firstrep_user') or {}).get('id')


def prepare_log(kind):
    from services.browser_auth import restore_session
    restore_session()
    user_id = owner()
    # Also defend against account changes made outside the standard login UI.
    if st.session_state.get('_tracking_owner') != user_id:
        change_user(st.session_state.get('firstrep_user'))
    st.session_state['_tracking_owner'] = user_id
    if st.session_state.pop(f'{kind}_reset_editor', False):
        st.session_state.pop(f'{kind}_editor', None)
    if user_id:
        st.caption('Saved to your account. Your logs will be here when you sign in again.')
        reload = st.button('Reload saved log', key=f'{kind}_reload')
        if kind not in st.session_state or reload:
            try:
                records = storage.load(user_id, kind)
                st.session_state[kind] = records
                st.session_state.pop(f'{kind}_editor', None)
            except StorageError as error:
                st.error(str(error))
                st.stop()
        guest = st.session_state.get('_guest_logs', {}).get(kind, [])
        if guest:
            st.info(f'{len(guest)} guest entries are available from before you signed in.')
            if st.button('Add guest entries to my account', key=f'{kind}_import_guest'):
                try:
                    append_records(kind, guest)
                    st.session_state['_guest_logs'].pop(kind, None)
                    st.rerun()
                except (ValueError, StorageError) as error:
                    st.error(str(error))
    else:
        st.caption('Guest mode: sign in on the home page to save your logs between visits. Guest entries last only for this browser session.')
        st.session_state.setdefault(kind, [])


def _with_ids(kind, records):
    clean = validate(kind, records)
    return [dict(row, id=str(original.get('id') or uuid4())) for row, original in zip(clean, records)]


def append_records(kind, records):
    clean = validate(kind, records)
    if owner():
        # Keep request IDs until a commit is confirmed, preventing duplicate retries.
        pending_key = f'{kind}_pending_append'
        pending = st.session_state.get(pending_key)
        comparison = [{key: value for key, value in row.items() if key != 'recorded_at'} for row in clean] if kind == 'bmi_log' else clean
        if not pending or pending['inputs'] != comparison:
            pending = {'inputs': comparison, 'rows': _with_ids(kind, clean)}
            st.session_state[pending_key] = pending
        saved = storage.append(owner(), kind, pending['rows'])
        st.session_state[kind] = saved
        st.session_state.pop(pending_key, None)
    else:
        st.session_state.setdefault(kind, []).extend(clean)
    # Appends happen before the editor is rendered on this run.
    st.session_state.pop(f'{kind}_editor', None)


def replace_records(kind, records, preserve_ids=False):
    clean = validate(kind, records)
    if owner():
        existing = st.session_state[kind]
        allowed = {row['id'] for row in existing}
        if preserve_ids:
            for row in records:
                row_id = row.get('id')
                if pd.notna(row_id) and row_id and row_id not in allowed:
                    raise ValueError('Unknown entry ID. Reload the saved log and try again.')
            originals = [dict(row, id=row.get('id') if pd.notna(row.get('id')) else None) for row in records]
        else:
            originals = clean
        pending_key = f'{kind}_pending_replace'
        pending = st.session_state.get(pending_key)
        if not pending or pending['inputs'] != originals:
            pending = {'inputs': originals, 'rows': _with_ids(kind, originals)}
            st.session_state[pending_key] = pending
        st.session_state[kind] = storage.replace(owner(), kind, existing, pending['rows'])
        st.session_state.pop(pending_key, None)
    else:
        st.session_state[kind] = clean
    st.session_state[f'{kind}_reset_editor'] = True


def number(value, label, low, high, integer=False):
    try:
        value = float(value)
    except (ValueError, TypeError):
        raise ValueError(f'{label} must be a number. Check your entry.') from None
    if not math.isfinite(value) or not low <= value <= high or (integer and not value.is_integer()):
        raise ValueError(f'{label} must be {"a whole number " if integer else ""}between {low} and {high}. Check your units and entry.')
    return int(value) if integer else value


def validate(kind, records):
    clean = []
    for index, row in enumerate(records, 1):
        try:
            result = {}
            for field in SCHEMAS[kind]:
                value = row[field]
                if field == 'recorded_at':
                    timestamp = datetime.fromisoformat(str(value))
                    if timestamp.tzinfo is not None:
                        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
                    result[field] = timestamp.isoformat()
                elif field == 'date':
                    result[field] = date.fromisoformat(str(value)[:10]).isoformat()
                elif field in ('exercise', 'food', 'notes'):
                    result[field] = '' if pd.isna(value) else ' '.join(str(value).split())
                    if field != 'notes' and not result[field]:
                        raise ValueError(f'{field.title()} is required. Enter a name.')
                else:
                    limits = {'height_cm': (100, 250), 'weight_kg': (20, 500) if kind == 'bmi_log' else (0, 1000), 'sets': (1, 100), 'reps': (1, 1000), 'rpe': (1, 10)}
                    result[field] = number(value, field.replace('_', ' ').title(), *limits.get(field, (0, 10000)), integer=field in ('sets', 'reps'))
                    if field == 'rpe' and result[field] * 2 % 1:
                        raise ValueError('RPE must use half-point steps.')
            clean.append(result)
        except (ValueError, TypeError, KeyError) as error:
            raise ValueError(f'Row {index}: {error}') from None
    return clean


def frame(kind):
    data = pd.DataFrame(st.session_state.setdefault(kind, []), columns=SCHEMAS[kind])
    if kind == 'bmi_log':
        data['bmi'] = data.weight_kg / (data.height_cm / 100) ** 2
    elif kind == 'workout_log':
        data['volume_kg'] = data.sets * data.reps * data.weight_kg
    else:
        data['calories'] = data.protein_g * 4 + data.carbs_g * 4 + data.fat_g * 9
    return data


def log_controls(kind, editable=False):
    st.caption('CSV downloads are optional backups of your saved account log.' if owner() else 'Download a CSV before leaving to keep a copy of your guest log.')
    raw = pd.DataFrame(st.session_state.setdefault(kind, []), columns=SCHEMAS[kind])
    editor_data = pd.DataFrame(st.session_state[kind], columns=['id', *SCHEMAS[kind]]) if owner() else raw
    if editable and not raw.empty:
        with st.expander('Edit full log'):
            st.caption('Edit inputs or delete rows, then save. Totals are recalculated. Weights here are in kilograms.')
            with st.form(f'{kind}_edit'):
                edited = st.data_editor(editor_data, num_rows='dynamic', hide_index=True, disabled=['id'], column_config={'id': None}, key=f'{kind}_editor')
                save = st.form_submit_button('Save changes')
            if save:
                try:
                    replace_records(kind, edited.to_dict('records'), preserve_ids=True)
                    st.rerun()
                except (ValueError, StorageError) as error:
                    st.error(str(error))
                    st.download_button('Download unsaved edits', edited[SCHEMAS[kind]].to_csv(index=False).encode(), file_name=f'{kind}_unsaved.csv', mime='text/csv')
    st.download_button('Download CSV', raw.to_csv(index=False).encode('utf-8'), file_name=f'{kind}.csv', mime='text/csv', key=f'{kind}_download')
    with st.expander('Restore from CSV'):
        st.caption('Restore replaces your saved account log.' if owner() else 'Restore replaces this session’s log. Download your current log first if you want to keep it.')
        confirmed = st.checkbox('Replace my saved log with this CSV', key=f'{kind}_confirm_restore') if owner() else True
        upload = st.file_uploader('Choose a previously downloaded CSV', type=['csv'], key=f'{kind}_upload')
        if st.button('Restore log', key=f'{kind}_restore'):
            if not confirmed:
                st.error('Select the replacement checkbox before restoring your account log.')
            elif upload is None:
                st.error('Choose a CSV file before restoring.')
            else:
                try:
                    if upload.size > 5_000_000:
                        raise ValueError('File exceeds 5 MB. Upload a smaller log.')
                    data = pd.read_csv(io.BytesIO(upload.getvalue()), keep_default_na=False)
                    if set(data.columns) != set(SCHEMAS[kind]):
                        raise ValueError('CSV columns do not match this log. Use a CSV downloaded from this tracker.')
                    records = validate(kind, data.to_dict('records'))
                    replace_records(kind, records)
                    st.rerun()
                except (ValueError, UnicodeError, pd.errors.ParserError, StorageError) as error:
                    st.error(f'Could not restore: {error}')
