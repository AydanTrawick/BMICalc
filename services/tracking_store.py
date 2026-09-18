"""Account-scoped, transactional persistence for tracker inputs."""
from datetime import datetime, timezone

from psycopg import Error, sql
from streamlit.errors import StreamlitSecretNotFoundError
from services.auth_service import get_database_connection, AuthConfigurationError

SCHEMAS = {
    'bmi_log': ['recorded_at', 'height_cm', 'weight_kg'],
    'workout_log': ['date', 'exercise', 'sets', 'reps', 'weight_kg', 'rpe', 'notes'],
    'food_log': ['date', 'food', 'protein_g', 'carbs_g', 'fat_g'],
}
TABLES = {
    'bmi_log': 'firstrep_bmi_readings',
    'workout_log': 'firstrep_workout_entries',
    'food_log': 'firstrep_food_entries',
}


class StorageError(RuntimeError):
    pass


class ConflictError(StorageError):
    pass


def _normalize(kind, row):
    result = {'id': str(row['id'])}
    for field in SCHEMAS[kind]:
        value = row[field]
        if field == 'recorded_at':
            value = value.astimezone(timezone.utc).replace(tzinfo=None).isoformat()
        elif field == 'date':
            value = value.isoformat()
        elif field == 'rpe':
            value = float(value)
        result[field] = value
    return result


def _read(cursor, user_id, kind):
    cursor.execute(sql.SQL('SELECT {} FROM public.{} WHERE user_id = %s ORDER BY {}, created_at, id').format(
        sql.SQL(', ').join(map(sql.Identifier, ['id', *SCHEMAS[kind]])),
        sql.Identifier(TABLES[kind]), sql.Identifier(SCHEMAS[kind][0])), (user_id,))
    return [_normalize(kind, row) for row in cursor.fetchall()]


def _lock(cursor, user_id):
    if not user_id:
        raise StorageError('Sign in before saving to your account.')
    # Serialize this account's writes; another account is never locked.
    cursor.execute('SELECT id FROM public.firstrep_users WHERE id = %s FOR UPDATE', (user_id,))
    if cursor.fetchone() is None:
        raise StorageError('Your account was not found. Sign out and sign in again.')


def _values(kind, row):
    values = [row[field] for field in SCHEMAS[kind]]
    if kind == 'bmi_log':
        timestamp = datetime.fromisoformat(values[0])
        values[0] = timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp
    return values


def _insert(cursor, user_id, kind, rows):
    columns = ['id', 'user_id', *SCHEMAS[kind], 'created_at']
    query = sql.SQL('INSERT INTO public.{} ({}) VALUES ({})').format(
        sql.Identifier(TABLES[kind]), sql.SQL(', ').join(map(sql.Identifier, columns)),
        sql.SQL(', ').join([*(sql.Placeholder() for _ in columns[:-1]), sql.SQL('clock_timestamp()')]))
    for row in rows:
        cursor.execute(query, [row['id'], user_id, *_values(kind, row)])


def load(user_id, kind):
    try:
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                return _read(cursor, user_id, kind)
    except (Error, AuthConfigurationError, StreamlitSecretNotFoundError) as error:
        raise StorageError('Could not load your saved log. Check the database connection and try again.') from error


def append(user_id, kind, rows):
    """Caller supplies stable IDs so retries after a lost response are safe."""
    try:
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                _lock(cursor, user_id)
                existing = {row['id']: row for row in _read(cursor, user_id, kind)}
                new = []
                for row in rows:
                    if row['id'] in existing:
                        if row != existing[row['id']]:
                            raise ConflictError('This entry changed. Reload your saved log before trying again.')
                    else:
                        new.append(row)
                _insert(cursor, user_id, kind, new)
                result = _read(cursor, user_id, kind)
        return result
    except (Error, AuthConfigurationError, StreamlitSecretNotFoundError) as error:
        raise StorageError('Could not confirm the save. Your input is still here; try saving again.') from error


def replace(user_id, kind, expected, desired):
    """Apply edits/imports only if the displayed snapshot is still current."""
    try:
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                _lock(cursor, user_id)
                current = _read(cursor, user_id, kind)
                before = {row['id']: row for row in expected}
                after = {row['id']: row for row in desired}
                actual = {row['id']: row for row in current}
                if len(after) != len(desired):
                    raise StorageError('Duplicate entry IDs. Reload your saved log and try again.')
                if actual == after:  # A previous attempt committed but its response was lost.
                    return current
                if actual != before:
                    raise ConflictError('This log changed in another session. Download your edits, then reload the saved log before editing again.')
                for row_id in before.keys() - after.keys():
                    cursor.execute(sql.SQL('DELETE FROM public.{} WHERE user_id = %s AND id = %s').format(sql.Identifier(TABLES[kind])), (user_id, row_id))
                assignments = sql.SQL(', ').join(sql.SQL('{} = %s').format(sql.Identifier(field)) for field in SCHEMAS[kind])
                for row_id in before.keys() & after.keys():
                    if before[row_id] != after[row_id]:
                        cursor.execute(sql.SQL('UPDATE public.{} SET {} WHERE user_id = %s AND id = %s').format(sql.Identifier(TABLES[kind]), assignments), [*_values(kind, after[row_id]), user_id, row_id])
                _insert(cursor, user_id, kind, [after[key] for key in after.keys() - before.keys()])
                result = _read(cursor, user_id, kind)
        return result
    except (Error, AuthConfigurationError, StreamlitSecretNotFoundError) as error:
        raise StorageError('Could not confirm the changes. Your edits are still here; try saving again.') from error
