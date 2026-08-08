"""Generated ctypes declarations.

This file is generated. Do not edit manually.
"""

from __future__ import annotations

import ctypes


__all__ = (
    "GENERATED_FUNCTIONS",
    "bind",
)


GENERATED_FUNCTIONS = (
    "ab_alphabet_select",
    "ab_utf8_byte_count",
    "ab_utf8_byte_offset",
    "ab_utf8_length",
)


def bind(dll: ctypes.CDLL) -> ctypes.CDLL:
    # C declaration:
    # PYTEST_API int ab_utf8_byte_count(const unsigned char *z)

    dll.ab_utf8_byte_count.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
    ]
    dll.ab_utf8_byte_count.restype = ctypes.c_int

    # C declaration:
    # PYTEST_API sqlite3_int64 ab_utf8_length(const char *z)

    dll.ab_utf8_length.argtypes = [
        ctypes.POINTER(ctypes.c_char),
    ]
    dll.ab_utf8_length.restype = ctypes.c_int64

    # C declaration:
    # PYTEST_API int ab_utf8_byte_offset(const char *z, sqlite3_int64 i)

    dll.ab_utf8_byte_offset.argtypes = [
        ctypes.POINTER(ctypes.c_char),
        ctypes.c_int64,
    ]
    dll.ab_utf8_byte_offset.restype = ctypes.c_int

    # C declaration:
    # PYTEST_API const char *ab_alphabet_select(const char *zLanguage)

    dll.ab_alphabet_select.argtypes = [
        ctypes.POINTER(ctypes.c_char),
    ]
    dll.ab_alphabet_select.restype = ctypes.POINTER(ctypes.c_char)

    return dll
