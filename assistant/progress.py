"""Transparent statistics from actual logged inputs, without guessed durations/reps."""
from collections import Counter, defaultdict
from datetime import date, timedelta

KG_PER_LB = .45359237
KM_PER_MILE = 1.609344


def summary(rows, start_date, end_date, today):
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    rows = sorted(rows, key=lambda row: (str(row['log_date']), row['id']))
    selected = [row for row in rows if start <= date.fromisoformat(str(row['log_date'])) <= end]
    counts = Counter(row['log_type'] for row in selected)
    sessions = {(str(row['log_date']), row['log_type']) for row in selected if row['log_type'] in ('strength', 'cardio')}
    by_type = Counter(kind for _, kind in sessions)
    distance, volume, incomplete = defaultdict(float), 0., 0
    weights, prs, records = [], [], {}
    for row in rows:
        details, kind = row['details'], row['log_type']
        in_range = start <= date.fromisoformat(str(row['log_date'])) <= end
        if kind == 'strength':
            weight, unit = details.get('weight'), details.get('unit')
            weight_kg = float(weight) * (KG_PER_LB if unit == 'lb' else 1) if weight is not None and unit in ('lb', 'kg') else None
            name = str(details.get('exercise', '')).casefold()
            reps, sets = details.get('reps'), details.get('sets')
            if in_range:
                if weight_kg is not None and str(reps).isdigit() and isinstance(sets, int):
                    volume += sets * int(reps) * weight_kg
                else:
                    incomplete += 1
            # Compare equal rep counts; a first observed lift establishes a baseline.
            if weight_kg is not None and str(reps).isdigit():
                key = (name, int(reps))
                if key in records and weight_kg > records[key] and in_range:
                    prs.append({'exercise': details['exercise'], 'reps': int(reps), 'weight_kg': round(weight_kg, 2), 'date': str(row['log_date'])})
                records[key] = max(records.get(key, 0), weight_kg)
        elif in_range and kind == 'cardio' and details.get('distance') is not None:
            unit = details.get('distance_unit')
            if unit in ('miles', 'km'):
                distance[details['activity']] += float(details['distance']) * (KM_PER_MILE if unit == 'miles' else 1)
        elif in_range and kind == 'bodyweight' and details.get('unit') in ('lb', 'kg'):
            weights.append(float(details['weight']) * (KG_PER_LB if details['unit'] == 'lb' else 1))
    training_dates = {date.fromisoformat(str(row['log_date'])) for row in rows if row['log_type'] in ('strength', 'cardio')}
    cursor = today if today in training_dates else today - timedelta(days=1)
    streak = 0
    while cursor in training_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return {'total_sessions': len(sessions), 'sessions_by_type': dict(by_type), 'entries_by_type': dict(counts),
            'total_cardio_distance_km': round(sum(distance.values()), 3),
            'cardio_distance_km_by_activity': {key: round(value, 3) for key, value in distance.items()},
            'total_strength_volume_kg': round(volume, 2), 'strength_entries_with_unknown_volume': incomplete,
            'current_streak_days': streak, 'streak_as_of': today.isoformat(), 'prs': prs,
            'bodyweight_change_kg': round(weights[-1] - weights[0], 2) if len(weights) >= 2 else None,
            'coverage': 'Assistant activity_logs only. Sessions mean distinct date/type pairs, not individually tracked gym visits. PRs compare recorded weight at equal reps against earlier active logs; first records are baselines. Streak counts training days only. Unknown values are excluded.'}
