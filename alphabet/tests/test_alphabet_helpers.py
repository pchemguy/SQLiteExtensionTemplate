from __future__ import annotations

from typing import Any

import pytest

LATIN = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
CYRILLIC = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя"


def copy_c_string(ffi: Any, pointer: Any) -> bytes | None:
    return None if pointer == ffi.NULL else ffi.string(pointer)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("A", 1, id="ascii-1-byte"),
        pytest.param("é", 2, id="latin-2-byte"),
        pytest.param("Я", 2, id="cyrillic-2-byte"),
        pytest.param("€", 3, id="euro-3-byte"),
        pytest.param("😀", 4, id="emoji-4-byte"),
    ],
)
def test_utf8_byte_count_valid_code_points(lib: Any, text: str, expected: int) -> None:
    assert lib.ab_utf8_byte_count(text.encode("utf-8")) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("", 0, id="empty"),
        pytest.param("ASCII", 5, id="ascii"),
        pytest.param("Aé€😀Z", 5, id="mixed-width"),
        pytest.param(LATIN, 52, id="latin-alphabet"),
        pytest.param(CYRILLIC, 66, id="cyrillic-alphabet"),
    ],
)
def test_utf8_length_counts_code_points(lib: Any, text: str, expected: int) -> None:
    assert lib.ab_utf8_length(text.encode("utf-8")) == expected


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        pytest.param(0, 0, id="start"),
        pytest.param(1, 1, id="after-ascii"),
        pytest.param(2, 3, id="after-2-byte"),
        pytest.param(3, 6, id="after-3-byte"),
        pytest.param(4, 10, id="after-4-byte"),
        pytest.param(5, 11, id="terminating-nul-offset"),
    ],
)
def test_utf8_byte_offset_mixed_width_string(lib: Any, index: int, expected: int) -> None:
    assert lib.ab_utf8_byte_offset("Aé€😀Z".encode("utf-8"), index) == expected


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("", id="empty"),
        pytest.param(LATIN, id="latin"),
        pytest.param(CYRILLIC, id="cyrillic"),
        pytest.param("Aé€😀Z", id="mixed-width"),
    ],
)
def test_utf8_byte_offset_at_end_equals_utf8_byte_length(lib: Any, text: str) -> None:
    encoded = text.encode("utf-8")
    code_points = len(text)
    assert lib.ab_utf8_byte_offset(encoded, code_points) == len(encoded)


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        pytest.param("en", LATIN, id="en"),
        pytest.param("English", LATIN, id="English"),
        pytest.param("EN", LATIN, id="EN-case-insensitive"),
        pytest.param("eNgLiSh", LATIN, id="English-mixed-case"),
        pytest.param("ru", CYRILLIC, id="ru"),
        pytest.param("Russian", CYRILLIC, id="Russian"),
        pytest.param("RU", CYRILLIC, id="RU-case-insensitive"),
        pytest.param("rUsSiAn", CYRILLIC, id="Russian-mixed-case"),
    ],
)
def test_alphabet_select_supported_aliases(
    ffi: Any, lib: Any, language: str, expected: str
) -> None:
    pointer = lib.ab_alphabet_select(language.encode("utf-8"))
    assert pointer != ffi.NULL
    assert copy_c_string(ffi, pointer) == expected.encode("utf-8")


@pytest.mark.parametrize(
    "language",
    [
        pytest.param("", id="empty"),
        pytest.param("eng", id="abbreviation-not-supported"),
        pytest.param("de", id="unsupported-language"),
        pytest.param("Englishx", id="near-match"),
        pytest.param("русский", id="non-ascii-name"),
    ],
)
def test_alphabet_select_unsupported_returns_null(
    ffi: Any, lib: Any, language: str
) -> None:
    assert lib.ab_alphabet_select(language.encode("utf-8")) == ffi.NULL
