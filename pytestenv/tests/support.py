__all__ = [
    "LATIN",
    "CYRILLIC",
    "LANGUAGE_ERROR",
    "LANGUAGE_TYPE_ERROR",
    "START_TYPE_ERROR",
    "START_RANGE_ERROR",
    "LENGTH_TYPE_ERROR",
    "LENGTH_RANGE_ERROR",
]


LATIN = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
)

CYRILLIC = (
    "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
)

LANGUAGE_ERROR = (
    "alpha_string() language must be en, English, ru, or Russian"
)

LANGUAGE_TYPE_ERROR = "alpha_string() language must be text"
START_TYPE_ERROR    = "alpha_string() start must be an integer"
START_RANGE_ERROR   = "alpha_string() start index is out of range"
LENGTH_TYPE_ERROR   = "alpha_string() length must be an integer"
LENGTH_RANGE_ERROR  = "alpha_string() length must not be negative"
