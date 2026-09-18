from datetime import date

import pytest

from assistant.config import AssistantError
from assistant.dates import parse_date, resolve_date_arguments

TODAY = date(2026, 9, 17)


@pytest.mark.parametrize('text,expected', [('today', '2026-09-17'), ('yesterday', '2026-09-16'),
                                        ('last Monday', '2026-09-14'), ('9/15', '2026-09-15'),
                                        ('three days ago', '2026-09-14')])
def test_relative_dates(text, expected):
    assert parse_date(text, TODAY).isoformat() == expected


@pytest.mark.parametrize('text', ['2026-09-18', '2025-09-16', '2/30', 'whenever', 'tomorrow'])
def test_invalid_future_and_old_dates(text):
    with pytest.raises(AssistantError):
        parse_date(text, TODAY)


def test_python_resolves_user_phrase_over_model_guess_and_calendar_ranges():
    assert resolve_date_arguments({'date': '2026-09-15'}, 'Log my run yesterday', TODAY)['date'] == '2026-09-16'
    assert resolve_date_arguments({'start_date': 'wrong', 'end_date': 'wrong'}, 'legs last week', TODAY) == {
        'start_date': '2026-09-07', 'end_date': '2026-09-13'}
    assert resolve_date_arguments({'start_date': 'wrong', 'end_date': 'wrong'}, 'How am I doing this month?', TODAY)['start_date'] == '2026-09-01'
    assert resolve_date_arguments({'start_date': '2026-09-01', 'end_date': '2026-09-01'}, 'What did I do yesterday?', TODAY) == {
        'start_date': '2026-09-16', 'end_date': '2026-09-16'}
    with pytest.raises(AssistantError, match='Future'):
        resolve_date_arguments({'date': '2026-09-17'}, 'Log a run tomorrow', TODAY)
