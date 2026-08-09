# ruff: noqa: ANN001, ANN201
from __future__ import annotations

import pytest

from tests.cffi_types import CffiValue


@pytest.mark.parametrize(
    ("pointer", "count", "expected_status", "expected", "output_changes"),
    [
        pytest.param("null", 0, "CTD_OK", 0, True, id="null-zero-count"),
        pytest.param("null", 1, "CTD_ERROR_NULL", 777, False, id="null-nonzero-count"),
        pytest.param("array", 3, "CTD_OK", 6, True, id="non-null-nonzero-count"),
    ],
)
def test_sum_nullable_pointer_contract(
    ffi: CffiValue,
    lib: CffiValue,
    pointer: str,
    count: int,
    expected_status: str,
    expected: int,
    output_changes: bool,
) -> None:
    values = ffi.NULL if pointer == "null" else ffi.new("int32_t[]", [1, 2, 3])
    result = ffi.new("int64_t *", 777)
    assert lib.ctd_sum_i32(values, count, result) == getattr(lib, expected_status)
    assert result[0] == expected
    assert (result[0] != 777) is output_changes


@pytest.mark.parametrize(
    ("values", "factor", "expected"),
    [
        pytest.param([], 9, [], id="empty"),
        pytest.param([7], -2, [-14], id="singleton"),
        pytest.param([1, -2, 3], 3, [3, -6, 9], id="mixed"),
    ],
)
def test_scale_arrays(
    ffi: CffiValue, lib: CffiValue, values: list[int], factor: int, expected: list[int]
) -> None:
    array = ffi.NULL if not values else ffi.new("int32_t[]", values)
    assert lib.ctd_scale_i32(array, len(values), factor) == lib.CTD_OK
    assert ([] if array == ffi.NULL else list(array)) == expected


def test_scale_overflow_does_not_partially_modify_array(
    ffi: CffiValue, lib: CffiValue
) -> None:
    values = ffi.new("int32_t[]", [3, 2**30])
    assert lib.ctd_scale_i32(values, 2, 2) == lib.CTD_ERROR_RANGE
    assert list(values) == [3, 2**30]


@pytest.mark.parametrize(
    ("capacity", "size_query", "expected_status", "storage_written"),
    [
        pytest.param(0, True, "CTD_ERROR_CAPACITY", False, id="size-query"),
        pytest.param(3, False, "CTD_ERROR_CAPACITY", False, id="one-short"),
        pytest.param(4, False, "CTD_OK", True, id="exact-capacity"),
        pytest.param(5, False, "CTD_OK", True, id="extra-capacity"),
    ],
)
def test_sequence_capacity_contract(
    ffi: CffiValue,
    lib: CffiValue,
    capacity: int,
    size_query: bool,
    expected_status: str,
    storage_written: bool,
) -> None:
    sentinel = [777] * 5
    buffer = ffi.NULL if size_query else ffi.new("int32_t[]", sentinel)
    required = ffi.new("size_t *", 999)
    status = lib.ctd_make_sequence_i32(10, 4, buffer, capacity, required)
    assert status == getattr(lib, expected_status)
    assert required[0] == 4
    if not size_query:
        expected = [10, 11, 12, 13, 777] if storage_written else sentinel
        assert list(buffer) == expected
        assert (list(buffer) != sentinel) is storage_written


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        pytest.param(b"", 0, id="empty"),
        pytest.param(b"A\x00B", 131, id="embedded-nul"),
        pytest.param(b"\x00\xff\x01", 256, id="contains-ff"),
    ],
)
def test_byte_checksum(
    ffi: CffiValue, lib: CffiValue, payload: bytes, expected: int
) -> None:
    data = ffi.NULL if not payload else ffi.new("uint8_t[]", payload)
    result = ffi.new("uint32_t *", 0xDEADBEEF)
    assert lib.ctd_checksum_bytes(data, len(payload), result) == lib.CTD_OK
    assert result[0] == expected


@pytest.mark.parametrize(
    ("capacity", "size_query", "expected_status", "storage_written"),
    [
        pytest.param(0, True, "CTD_ERROR_CAPACITY", False, id="size-query"),
        pytest.param(3, False, "CTD_ERROR_CAPACITY", False, id="one-short"),
        pytest.param(4, False, "CTD_OK", True, id="exact-capacity"),
        pytest.param(5, False, "CTD_OK", True, id="extra-capacity"),
    ],
)
def test_copy_bytes_capacity_contract(
    ffi: CffiValue,
    lib: CffiValue,
    capacity: int,
    size_query: bool,
    expected_status: str,
    storage_written: bool,
) -> None:
    source = ffi.new("uint8_t[]", b"abcd")
    sentinel = b"XXXXX"
    destination = ffi.NULL if size_query else ffi.new("uint8_t[]", sentinel)
    required = ffi.new("size_t *", 999)
    status = lib.ctd_copy_bytes(source, 4, destination, capacity, required)
    assert status == getattr(lib, expected_status)
    assert required[0] == 4
    if not size_query:
        expected = b"abcdX" if storage_written else sentinel
        actual = bytes(ffi.buffer(destination, len(sentinel)))
        assert actual == expected
        assert (actual != sentinel) is storage_written
