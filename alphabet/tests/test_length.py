import pytest

from .support import (
    CYRILLIC,
    LATIN,
    LENGTH_RANGE_ERROR,
    LENGTH_TYPE_ERROR,
)


@pytest.mark.parametrize(
    ("language", "alphabet"),
    [
        ("en", LATIN),
        ("ru", CYRILLIC),
    ],
)
@pytest.mark.parametrize(
    ("start", "length"),
    [
        (0, 0),
        (0, 1),
        (1, 1),
        (2, 5),
        (-1, 1),
        (-5, 2),
        (-5, 5),
        (-5, 1000),
    ],
)
def test_valid_length(
    scalar,
    language: str,
    alphabet: str,
    start: int,
    length: int,
) -> None:
    normalized_start = start if start >= 0 else len(alphabet) + start
    expected = alphabet[normalized_start:normalized_start + length]

    assert scalar("SELECT alpha_string(?, ?, ?)", (language, start, length)) == expected


@pytest.mark.parametrize(
    "length",
    [
        -1,
        -2,
        -(2**63),
    ],
)
def test_negative_length(assert_sql_error, length: int) -> None:
    assert_sql_error(LENGTH_RANGE_ERROR, "SELECT alpha_string('en', 0, ?)", (length,))


@pytest.mark.parametrize(
    "length",
    [
        1.0,
        "1",
        b"1",
    ],
)
def test_length_must_be_integer(assert_sql_error, length) -> None:
    assert_sql_error(LENGTH_TYPE_ERROR, "SELECT alpha_string('en', 0, ?)", (length,))


def test_large_length_is_truncated(scalar) -> None:
    assert scalar("SELECT alpha_string('en', 50, ?)", (2**63 - 1,)) == "yz"
