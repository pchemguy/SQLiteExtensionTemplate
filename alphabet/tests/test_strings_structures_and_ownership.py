# ruff: noqa: ANN001, ANN201
from __future__ import annotations

import pytest

from tests.cffi_types import CffiValue


def copy_nullable_string(ffi: CffiValue, pointer: CffiValue) -> bytes | None:
    return None if pointer == ffi.NULL else ffi.string(pointer)


def unpack_i32(ffi: CffiValue, pointer: CffiValue, count: int) -> list[int]:
    return list(ffi.unpack(pointer, count))


def copy_descriptor(ffi: CffiValue, descriptor: CffiValue) -> tuple[bytes, list[int]]:
    return ffi.string(descriptor.message), unpack_i32(
        ffi, descriptor.values, descriptor.count
    )


def copy_node(
    ffi: CffiValue, node: CffiValue
) -> tuple[int, object | None, object | None] | None:
    if node == ffi.NULL:
        return None
    return node.value, copy_node(ffi, node.next), copy_node(ffi, node.child)


@pytest.mark.parametrize(
    ("initial", "capacity", "expected"),
    [
        pytest.param(b"mixed Case", 11, b"MIXED CASE", id="ascii-lowercase"),
        pytest.param(b"UPPER", 6, b"UPPER", id="already-uppercase"),
        pytest.param(b"123", 4, b"123", id="digits"),
        pytest.param(b"", 1, b"", id="empty"),
    ],
)
def test_ascii_upper_success(
    ffi: CffiValue, lib: CffiValue, initial: bytes, capacity: int, expected: bytes
) -> None:
    storage = ffi.new("char[]", initial + b"\0")
    assert lib.ctd_ascii_upper(storage, capacity) == lib.CTD_OK
    assert bytes(ffi.buffer(storage, len(initial))) == expected


@pytest.mark.parametrize(
    ("initial", "capacity", "expected_status", "storage_written"),
    [
        pytest.param(
            b"lower", 5, "CTD_ERROR_CAPACITY", False, id="unterminated-capacity"
        ),
    ],
)
def test_ascii_upper_failure_preserves_storage(
    ffi: CffiValue,
    lib: CffiValue,
    initial: bytes,
    capacity: int,
    expected_status: str,
    storage_written: bool,
) -> None:
    storage = ffi.new("char[]", initial + b"\0")
    before = bytes(ffi.buffer(storage, len(initial)))
    assert lib.ctd_ascii_upper(storage, capacity) == getattr(lib, expected_status)
    after = bytes(ffi.buffer(storage, len(initial)))
    assert after == initial
    assert (after != before) is storage_written


@pytest.mark.parametrize(
    ("capacity", "size_query", "expected_status", "storage_written"),
    [
        pytest.param(0, True, "CTD_ERROR_CAPACITY", False, id="size-query"),
        pytest.param(5, False, "CTD_ERROR_CAPACITY", False, id="one-short"),
        pytest.param(6, False, "CTD_OK", True, id="exact-capacity"),
        pytest.param(7, False, "CTD_OK", True, id="extra-capacity"),
    ],
)
def test_copy_string_capacity_contract(
    ffi: CffiValue,
    lib: CffiValue,
    capacity: int,
    size_query: bool,
    expected_status: str,
    storage_written: bool,
) -> None:
    sentinel = b"XXXXXXXX"
    destination = ffi.NULL if size_query else ffi.new("char[]", sentinel)
    required = ffi.new("size_t *", 999)
    status = lib.ctd_copy_string(b"hello", destination, capacity, required)
    assert status == getattr(lib, expected_status)
    assert required[0] == 6
    if not size_query:
        expected = b"hello\0XX" if storage_written else sentinel
        actual = bytes(ffi.buffer(destination, len(sentinel)))
        assert actual == expected
        assert (actual != sentinel) is storage_written


@pytest.mark.parametrize(
    ("left", "right", "expected_sum", "expected_dot"),
    [
        pytest.param((2.0, 3.0), (4.0, 5.0), (6.0, 8.0), 23.0, id="ordinary"),
        pytest.param((-2.0, -3.0), (4.0, -5.0), (2.0, -8.0), 7.0, id="negative"),
        pytest.param((0.0, 0.0), (0.0, 0.0), (0.0, 0.0), 0.0, id="zero"),
    ],
)
def test_point_operations(
    ffi: CffiValue,
    lib: CffiValue,
    left: CffiValue,
    right: CffiValue,
    expected_sum: CffiValue,
    expected_dot: CffiValue,
) -> None:
    a = lib.ctd_point_make(*left)
    b = lib.ctd_point_make(*right)
    combined = lib.ctd_point_add(a, b)
    assert combined.x == pytest.approx(expected_sum[0])
    assert combined.y == pytest.approx(expected_sum[1])
    assert lib.ctd_point_dot(ffi.addressof(a), ffi.addressof(b)) == pytest.approx(
        expected_dot
    )


@pytest.mark.parametrize(
    ("values", "expected_minimum", "expected_maximum", "expected_sum", "expected_mean"),
    [
        pytest.param([1, 2, 3, 4], 1, 4, 10, 2.5, id="ascending"),
        pytest.param([-5, 10, -1], -5, 10, 4, 4.0 / 3.0, id="mixed-sign"),
        pytest.param([7], 7, 7, 7, 7.0, id="singleton"),
    ],
)
def test_compute_stats_success(
    ffi: CffiValue,
    lib: CffiValue,
    values: list[int],
    expected_minimum: int,
    expected_maximum: int,
    expected_sum: int,
    expected_mean: float,
) -> None:
    source = ffi.new("int32_t[]", values)
    result = ffi.new("ctd_stats *", {"count": 999, "mean": 987.25})
    assert lib.ctd_compute_stats_i32(source, len(values), result) == lib.CTD_OK
    assert result.count == len(values)
    assert result.minimum == expected_minimum
    assert result.maximum == expected_maximum
    assert result.sum == expected_sum
    assert result.mean == pytest.approx(expected_mean)


@pytest.mark.parametrize(
    ("values", "count", "expected_status", "output_changes"),
    [
        pytest.param(None, 1, "CTD_ERROR_NULL", False, id="null-values"),
        pytest.param([], 0, "CTD_ERROR_RANGE", False, id="zero-count"),
    ],
)
def test_compute_stats_failure_preserves_output(
    ffi: CffiValue,
    lib: CffiValue,
    values: list[int] | None,
    count: int,
    expected_status: str,
    output_changes: bool,
) -> None:
    source = ffi.NULL if values is None else ffi.new("int32_t[]", values)
    sentinel = {"count": 999, "minimum": -99, "maximum": 99, "sum": 777, "mean": 987.25}
    result = ffi.new("ctd_stats *", sentinel)
    assert lib.ctd_compute_stats_i32(source, count, result) == getattr(
        lib, expected_status
    )
    actual = {
        "count": result.count,
        "minimum": result.minimum,
        "maximum": result.maximum,
        "sum": result.sum,
        "mean": result.mean,
    }
    assert actual == pytest.approx(sentinel)
    assert (actual != sentinel) is output_changes


@pytest.mark.parametrize(
    ("kind", "value", "expected"),
    [
        pytest.param("i64", -42, -42.0, id="i64"),
        pytest.param("f64", 3.25, 3.25, id="f64"),
    ],
)
def test_tagged_union_conversions(
    ffi: CffiValue,
    lib: CffiValue,
    kind: CffiValue,
    value: CffiValue,
    expected: CffiValue,
) -> None:
    if kind == "i64":
        tagged = lib.ctd_value_from_i64(value)
    elif kind == "f64":
        tagged = lib.ctd_value_from_f64(value)
    result = ffi.new("double *", 123.5)
    assert lib.ctd_value_as_f64(ffi.addressof(tagged), result) == lib.CTD_OK
    assert result[0] == pytest.approx(expected)


@pytest.mark.parametrize(
    ("kind", "expected_status", "expected", "output_changes"),
    [
        pytest.param(999, "CTD_ERROR_RANGE", 123.5, False, id="invalid-discriminant"),
    ],
)
def test_tagged_union_conversion_failure_preserves_output(
    ffi: CffiValue,
    lib: CffiValue,
    kind: int,
    expected_status: str,
    expected: float,
    output_changes: bool,
) -> None:
    tagged = lib.ctd_value_from_i64(0)
    tagged.kind = kind
    sentinel = 123.5
    result = ffi.new("double *", sentinel)
    assert lib.ctd_value_as_f64(ffi.addressof(tagged), result) == getattr(
        lib, expected_status
    )
    assert result[0] == pytest.approx(expected)
    assert (result[0] != sentinel) is output_changes


def test_descriptor_helper_copies_borrowed_nested_data(
    ffi: CffiValue, lib: CffiValue
) -> None:
    assert copy_descriptor(ffi, lib.ctd_static_descriptor()) == (
        b"static Fibonacci descriptor",
        [8, 13, 21],
    )


def test_recursive_node_descriptor_copy(ffi: CffiValue) -> None:
    child = ffi.new("ctd_node *", {"value": 3})
    tail = ffi.new("ctd_node *", {"value": 2, "child": child})
    root = ffi.new("ctd_node *", {"value": 1, "next": tail})

    assert copy_node(ffi, root) == (1, (2, None, (3, None, None)), None)


def test_borrowed_sequence_is_copied_to_python_storage(
    ffi: CffiValue, lib: CffiValue
) -> None:
    count = ffi.new("size_t *")
    borrowed = lib.ctd_borrow_sequence_i32(count)

    assert borrowed != ffi.NULL
    copied = unpack_i32(ffi, borrowed, count[0])
    assert copied == [2, 3, 5, 7, 11]


def test_owned_greeting_uses_explicit_try_finally(
    ffi: CffiValue, lib: CffiValue
) -> None:
    greeting = lib.ctd_alloc_greeting(b"Pytest")
    assert greeting != ffi.NULL
    try:
        assert copy_nullable_string(ffi, greeting) == b"Hello, Pytest!"
    finally:
        lib.ctd_free(greeting)


def test_allocated_sequence_fixture(
    ffi: CffiValue, allocated_sequence: CffiValue
) -> None:
    values, count = allocated_sequence
    assert unpack_i32(ffi, values, count) == [-2, -1, 0, 1]


def test_counter_handle_fixture(
    ffi: CffiValue, lib: CffiValue, counter_handle: CffiValue
) -> None:
    result = ffi.new("int *", -999)
    assert lib.ctd_counter_add(counter_handle, 5, result) == lib.CTD_OK
    assert result[0] == 15


def test_accumulator_opaque_handle_lifecycle(ffi: CffiValue, lib: CffiValue) -> None:
    accumulator = lib.ctd_accumulator_create(2)
    assert accumulator != ffi.NULL
    try:
        assert lib.ctd_accumulator_add(accumulator, 20) == lib.CTD_OK
        assert lib.ctd_accumulator_add(accumulator, 22) == lib.CTD_OK
        result = ffi.new("int64_t *", -999)
        assert lib.ctd_accumulator_get(accumulator, result) == lib.CTD_OK
        assert result[0] == 42
    finally:
        lib.ctd_accumulator_destroy(accumulator)


def test_null_handle_failure_preserves_output(ffi: CffiValue, lib: CffiValue) -> None:
    result = ffi.new("int *", -999)
    assert lib.ctd_counter_get(ffi.NULL, result) == lib.CTD_ERROR_NULL
    assert result[0] == -999


@pytest.mark.parametrize(
    ("count", "is_null"),
    [pytest.param(0, True, id="zero-count"), pytest.param(1, False, id="one-element")],
)
def test_alloc_sequence_null_failure_behavior(
    ffi: CffiValue, lib: CffiValue, count: int, is_null: bool
) -> None:
    pointer = lib.ctd_alloc_sequence_i32(4, count)
    if is_null:
        assert pointer == ffi.NULL
    else:
        assert pointer != ffi.NULL
        lib.ctd_free(pointer)
