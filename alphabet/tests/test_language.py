import pytest

from .support import (
    CYRILLIC,
    LANGUAGE_ERROR,
    LANGUAGE_TYPE_ERROR,
    LATIN,
)


@pytest.mark.parametrize(
    "language",
    [
        "en",
        "EN",
        "eN",
        "English",
        "ENGLISH",
        "eNgLiSh",
    ],
)
def test_english_selectors(scalar, language: str) -> None:
    assert scalar("SELECT alpha_string(?)", (language,)) == LATIN


@pytest.mark.parametrize(
    "language",
    [
        "ru",
        "RU",
        "rU",
        "Russian",
        "RUSSIAN",
        "rUsSiAn",
    ],
)
def test_russian_selectors(scalar, language: str) -> None:
    assert scalar("SELECT alpha_string(?)", (language,)) == CYRILLIC


@pytest.mark.parametrize(
    "language",
    [
        "",
        "eng",
        "rus",
        "de",
        " English",
        "English ",
        "русский",
    ],
)
def test_unsupported_language(assert_sql_error, language: str) -> None:
    assert_sql_error(LANGUAGE_ERROR, "SELECT alpha_string(?)", (language,))


@pytest.mark.parametrize(
    "language",
    [
        1,
        1.0,
        b"en",
    ],
)
def test_language_must_be_text(assert_sql_error, language) -> None:
    assert_sql_error(LANGUAGE_TYPE_ERROR, "SELECT alpha_string(?)", (language,))
