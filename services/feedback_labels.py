"""Label normalization and fuzzy matching for classifier feedback corrections."""
import difflib
import re

MAX_LABEL_LENGTH = 60
FUZZY_MATCH_CUTOFF = 0.8

_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_PUNCT_RE = re.compile(r"[.,;:!?]+$")


class InvalidLabelError(ValueError):
    pass


def normalize_label(raw: str) -> str:
    """Lowercase, strip, collapse internal whitespace, and drop trailing punctuation."""
    if raw is None:
        raise InvalidLabelError("Label cannot be empty.")

    value = _WHITESPACE_RE.sub(" ", raw.strip()).lower()
    value = _TRAILING_PUNCT_RE.sub("", value).strip()

    if not value:
        raise InvalidLabelError("Label cannot be empty.")
    if len(value) > MAX_LABEL_LENGTH:
        raise InvalidLabelError(f"Label must be {MAX_LABEL_LENGTH} characters or fewer.")

    return value


def normalized_class_names(class_names: list[str]) -> dict[str, str]:
    """Map normalized class name -> original class name."""
    return {normalize_label(name): name for name in class_names}


def suggest_close_match(label: str, class_names: list[str]) -> str | None:
    """Return the original-cased known class closest to `label`, if any."""
    lookup = normalized_class_names(class_names)
    matches = difflib.get_close_matches(label, lookup.keys(), n=1, cutoff=FUZZY_MATCH_CUTOFF)
    return lookup[matches[0]] if matches else None


def is_known_class(label: str, class_names: list[str]) -> bool:
    return label in normalized_class_names(class_names)
