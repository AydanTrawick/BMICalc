"""Resolve the user's literal date phrases, rather than LLM calendar arithmetic."""
import re
from datetime import date, datetime, timedelta

from dateutil.parser import parse, ParserError
from dateutil.relativedelta import relativedelta

from assistant.config import AssistantError, today

WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
NUMBERS = dict(zip(['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'], range(1, 11)))
RELATIVE_PATTERN = r'\b(?:today|yesterday|last (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten) days? ago)\b'


def parse_date(value, anchor=None):
    anchor = anchor or today()
    text = str(value or 'today').strip().lower()
    if text == 'today':
        result = anchor
    elif text == 'yesterday':
        result = anchor - timedelta(days=1)
    elif text.startswith('last ') and text[5:] in WEEKDAYS:
        difference = (anchor.weekday() - WEEKDAYS.index(text[5:])) % 7 or 7
        result = anchor - timedelta(days=difference)
    elif match := re.fullmatch(r'(\d+|' + '|'.join(NUMBERS) + r') days? ago', text):
        count = NUMBERS.get(match[1], int(match[1]) if match[1].isdigit() else 0)
        result = anchor - timedelta(days=count)
    else:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?', text):
            raise AssistantError('Use today, yesterday, last Monday, a number of days ago, or a date such as 2026-09-15 or 9/15.')
        try:
            result = parse(text, default=datetime(anchor.year, 1, 1), dayfirst=False).date()
        except (ParserError, ValueError, OverflowError):
            raise AssistantError('That date is not valid. Please use YYYY-MM-DD.') from None
    if result > anchor or result < anchor - relativedelta(years=1):
        raise AssistantError('Choose a date within the past year, including today. Future dates cannot be logged.')
    return result


def resolve_date_arguments(arguments, user_text, anchor=None):
    """Use a unique explicit phrase from the user even if the model miscalculates it."""
    anchor = anchor or today()
    data = dict(arguments)
    text = user_text.lower()
    phrases = re.findall(RELATIVE_PATTERN + r'|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b', text)
    phrases = list(dict.fromkeys(phrases))
    if any(key in data for key in ('date', 'start_date', 'end_date')) and re.search(r'\b(?:tomorrow|next (?:week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b', text):
        raise AssistantError('Future dates cannot be logged or queried. Please choose today or a past date.')
    if 'date' in data:
        if len(phrases) == 1:
            data['date'] = phrases[0]
        data['date'] = parse_date(data['date'], anchor).isoformat()
    if 'start_date' in data and 'end_date' in data:
        if 'last week' in text:
            end = anchor - timedelta(days=anchor.weekday() + 1)
            data.update(start_date=end - timedelta(days=6), end_date=end)
        elif 'this week' in text:
            data.update(start_date=anchor - timedelta(days=anchor.weekday()), end_date=anchor)
        elif 'this month' in text:
            data.update(start_date=anchor.replace(day=1), end_date=anchor)
        elif 'last month' in text:
            end = anchor.replace(day=1) - timedelta(days=1)
            data.update(start_date=end.replace(day=1), end_date=end)
        elif len(phrases) == 1:
            day = parse_date(phrases[0], anchor)
            data.update(start_date=day, end_date=anchor if 'since' in text else day)
        elif len(phrases) == 2:
            data.update(start_date=parse_date(phrases[0], anchor), end_date=parse_date(phrases[1], anchor))
        for field in ('start_date', 'end_date'):
            data[field] = parse_date(data[field], anchor).isoformat()
        if data['start_date'] > data['end_date']:
            raise AssistantError('The start date must be on or before the end date.')
    return data
