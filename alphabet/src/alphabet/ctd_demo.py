"""
Demonstrate the complete C API exposed by ``_ctd_wrapper``.
"""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path
from typing import Any, TypeAlias, cast

MODULE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE_DIR))
sys.path.insert(0, str(MODULE_DIR.parent))

CffiValue: TypeAlias = Any
_wrapper = import_module("_cffi_wrapper")
ffi: CffiValue = _wrapper.ffi
lib: CffiValue = _wrapper.lib


def heading(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def c_string(pointer: CffiValue) -> str | None:
    if pointer == ffi.NULL:
        return None
    return cast(bytes, ffi.string(pointer)).decode("utf-8")


def status_name(status: int) -> str:
    return c_string(lib.ctd_status_name(status)) or "<null>"


def show_status(label: str, status: int) -> None:
    print(f"{label}: {status_name(status)} ({status})")


def point_tuple(point: CffiValue) -> tuple[float, float]:
    return point.x, point.y


def demo_globals_and_status_values() -> None:
    # Recommended canonical pattern catalogue - 1. Globals and status values.
    heading("Version, enum constants, and exported globals")

    print(f"ctd_version(): {c_string(lib.ctd_version())}")
    print(
        "status constants:",
        {
            "CTD_OK": lib.CTD_OK,
            "CTD_ERROR_NULL": lib.CTD_ERROR_NULL,
            "CTD_ERROR_RANGE": lib.CTD_ERROR_RANGE,
            "CTD_ERROR_CAPACITY": lib.CTD_ERROR_CAPACITY,
            "CTD_ERROR_ALLOCATION": lib.CTD_ERROR_ALLOCATION,
            "CTD_ERROR_DIVIDE_BY_ZERO": lib.CTD_ERROR_DIVIDE_BY_ZERO,
        },
    )
    print(
        "number-kind constants:",
        {
            "CTD_NUMBER_I64": lib.CTD_NUMBER_I64,
            "CTD_NUMBER_F64": lib.CTD_NUMBER_F64,
        },
    )
    print(
        "range-policy constants:",
        {
            "CTD_RANGE_REJECT": lib.CTD_RANGE_REJECT,
            "CTD_RANGE_CLAMP": lib.CTD_RANGE_CLAMP,
        },
    )
    library_name = cast(bytes, ffi.string(lib.ctd_library_name)).decode("utf-8")
    print(f"ctd_library_name: {library_name!r}")
    print(
        "read-only numeric constants:",
        {
            "ctd_max_supported_point_count": lib.ctd_max_supported_point_count,
            "ctd_numeric_epsilon": lib.ctd_numeric_epsilon,
        },
    )
    print(
        "ctd_origin_point fields:",
        {"x": lib.ctd_origin_point.x, "y": lib.ctd_origin_point.y},
    )

    lib.ctd_globals_reset()
    print(f"ctd_global_counter after reset: {lib.ctd_global_counter}")
    lib.ctd_global_counter = 40
    print(f"ctd_global_counter after direct assignment: {lib.ctd_global_counter}")
    lib.ctd_global_counter_reset()
    print(f"ctd_global_counter after counter reset: {lib.ctd_global_counter}")
    lib.ctd_global_counter = 40
    print(f"ctd_global_counter_increment(): {lib.ctd_global_counter_increment()}")
    print(f"ctd_global_counter now: {lib.ctd_global_counter}")
    lib.ctd_global_last_status = lib.CTD_ERROR_RANGE
    print(f"ctd_global_last_status after assignment: {lib.ctd_global_last_status}")
    lib.ctd_global_scale = 2.5
    print(f"ctd_global_scale after assignment: {lib.ctd_global_scale}")

    heading("Status-name lookup")

    for status in (
        lib.CTD_OK,
        lib.CTD_ERROR_NULL,
        lib.CTD_ERROR_RANGE,
        lib.CTD_ERROR_CAPACITY,
        lib.CTD_ERROR_ALLOCATION,
        lib.CTD_ERROR_DIVIDE_BY_ZERO,
        999,
    ):
        print(f"{status}: {status_name(status)}")

    # Pytest equivalent: assert lib.ctd_global_counter == 41
    assert lib.ctd_global_counter == 41


def demo_scalar_and_value_operations() -> None:
    # Recommended canonical pattern catalogue - 2. Scalar and value operations.
    heading("Scalar operations")

    print(f"ctd_add(17, 25): {lib.ctd_add(17, 25)}")
    print(f"ctd_add(INT_MAX, 1): {lib.ctd_add(2**31 - 1, 1)}")
    print(f"ctd_negate_i32(-123): {lib.ctd_negate_i32(-123)}")
    print(f"ctd_negate_i32(INT32_MIN): {lib.ctd_negate_i32(-(2**31))}")
    print(f"ctd_add_u64(2**63, 7): {lib.ctd_add_u64(2**63, 7)}")
    print(f"ctd_hypot_squared(3.0, 4.0): {lib.ctd_hypot_squared(3.0, 4.0)}")

    quotient = ffi.new("double *")
    status = lib.ctd_divide(22.0, 7.0, quotient)
    show_status("ctd_divide(22.0, 7.0)", status)
    print(f"result: {quotient[0]}")

    status = lib.ctd_divide(1.0, 0.0, quotient)
    show_status("ctd_divide(1.0, 0.0)", status)
    # Pytest equivalent: assert status == lib.CTD_ERROR_DIVIDE_BY_ZERO
    assert status == lib.CTD_ERROR_DIVIDE_BY_ZERO


def demo_scalar_pointer_operations() -> None:
    # Recommended canonical pattern catalogue - 3. Scalar pointer operations.
    heading("Scalar pointer operations")

    magic = ffi.new("int32_t *")
    status = lib.ctd_get_magic(magic)
    show_status("ctd_get_magic()", status)
    print(f"result: {magic[0]}")

    value = ffi.new("int32_t *", 41)
    status = lib.ctd_increment(value)
    show_status("ctd_increment()", status)
    print(f"value: {value[0]}")

    left = ffi.new("int32_t *", 10)
    right = ffi.new("int32_t *", 20)
    status = lib.ctd_swap_i32(left, right)
    show_status("ctd_swap_i32()", status)
    print(f"values: left={left[0]}, right={right[0]}")
    # Pytest equivalent: assert (left[0], right[0]) == (20, 10)
    assert (left[0], right[0]) == (20, 10)


def demo_typed_arrays() -> None:
    # Recommended canonical pattern catalogue - 4. Typed arrays.
    heading("Typed arrays and statistics")

    values = ffi.new("int32_t[]", [5, -2, 11, 4])
    total = ffi.new("int64_t *")

    status = lib.ctd_sum_i32(values, 4, total)
    show_status("ctd_sum_i32()", status)
    print(f"sum: {total[0]}")

    status = lib.ctd_reverse_i32(values, 4)
    show_status("ctd_reverse_i32()", status)
    print(f"reversed: {list(values)}")

    status = lib.ctd_scale_i32(values, 4, 2)
    show_status("ctd_scale_i32()", status)
    print(f"scaled: {list(values)}")

    stats = ffi.new("ctd_stats *")
    status = lib.ctd_compute_stats_i32(values, 4, stats)
    show_status("ctd_compute_stats_i32()", status)
    print(
        "stats:",
        {
            # A pointer-to-struct supports both spellings.  The indexed form is
            # useful when emphasizing that this is caller-allocated storage.
            "count": stats.count,
            "minimum": stats[0].minimum,
            "maximum": stats.maximum,
            "sum": stats.sum,
            "mean": stats.mean,
        },
    )

    heading("Caller-provided and library-allocated arrays")

    required_count = ffi.new("size_t *")
    status = lib.ctd_make_sequence_i32(
        100,
        5,
        ffi.NULL,
        0,
        required_count,
    )
    show_status("ctd_make_sequence_i32() size query", status)
    print(f"required elements: {required_count[0]}")

    sequence = ffi.new("int32_t[]", required_count[0])
    status = lib.ctd_make_sequence_i32(
        100,
        required_count[0],
        sequence,
        required_count[0],
        required_count,
    )
    show_status("ctd_make_sequence_i32() fill", status)
    print(f"sequence: {list(sequence)}")

    allocated = lib.ctd_alloc_sequence_i32(-3, 6)
    if allocated == ffi.NULL:
        raise MemoryError("ctd_alloc_sequence_i32() failed")

    try:
        print(f"allocated sequence: {list(ffi.unpack(allocated, 6))}")
    finally:
        lib.ctd_free(allocated)

    borrowed_count = ffi.new("size_t *")
    borrowed = lib.ctd_borrow_sequence_i32(borrowed_count)
    print(f"borrowed sequence: {list(ffi.unpack(borrowed, borrowed_count[0]))}")
    # Pytest equivalent: assert ffi.unpack(borrowed, borrowed_count[0]) == [...]
    assert list(ffi.unpack(borrowed, borrowed_count[0])) == [2, 3, 5, 7, 11]
    assert list(ffi.unpack(sequence, required_count[0])) == [100, 101, 102, 103, 104]


def demo_byte_buffers() -> None:
    # Recommended canonical pattern catalogue - 5. Byte buffers.
    heading("Byte buffers")

    source_bytes = b"\x00\x01\x7f\x80\xff"
    source = ffi.new("uint8_t[]", source_bytes)
    required_count = ffi.new("size_t *")

    status = lib.ctd_copy_bytes(
        source,
        len(source_bytes),
        ffi.NULL,
        0,
        required_count,
    )
    show_status("ctd_copy_bytes() size query", status)
    print(f"required bytes: {required_count[0]}")

    destination = ffi.new("uint8_t[]", required_count[0])
    status = lib.ctd_copy_bytes(
        source,
        len(source_bytes),
        destination,
        required_count[0],
        required_count,
    )
    show_status("ctd_copy_bytes() copy", status)
    print(f"copied bytes: {bytes(ffi.buffer(destination, required_count[0]))!r}")

    status = lib.ctd_xor_bytes(destination, required_count[0], 0xFF)
    show_status("ctd_xor_bytes()", status)
    print(f"XOR result: {bytes(ffi.buffer(destination, required_count[0]))!r}")

    checksum = ffi.new("uint32_t *")
    status = lib.ctd_checksum_bytes(source, len(source_bytes), checksum)
    show_status("ctd_checksum_bytes()", status)
    print(f"checksum: {checksum[0]}")
    # Pytest equivalent: assert bytes(ffi.buffer(destination, 5)) == expected
    assert bytes(ffi.buffer(destination, required_count[0])) == b"\xff\xfe\x80\x7f\x00"


def demo_strings() -> None:
    # Recommended canonical pattern catalogue - 6. Strings.
    heading("Strings")

    text = b"cffi"
    print(f"ctd_utf8_byte_size({text!r}): {lib.ctd_utf8_byte_size(text)}")
    print(f"ctd_utf8_byte_size(NULL): {lib.ctd_utf8_byte_size(ffi.NULL)}")

    for selector in (0, 1, 2, 99):
        selected = lib.ctd_select_static_string(selector)
        # Copy a borrowed string immediately; CTD retains ownership.
        copied = (
            None
            if selected == ffi.NULL
            else cast(bytes, ffi.string(selected)).decode("utf-8")
        )
        print(f"ctd_select_static_string({selector}): {copied!r}")

    greeting = lib.ctd_alloc_greeting(b"CFFI")
    if greeting == ffi.NULL:
        raise MemoryError("ctd_alloc_greeting() failed")

    try:
        print(f"ctd_alloc_greeting(): {c_string(greeting)!r}")
    finally:
        lib.ctd_free(greeting)

    upper_buffer = ffi.new("char[]", b"Mixed Case 123")
    status = lib.ctd_ascii_upper(upper_buffer, ffi.sizeof(upper_buffer))
    show_status("ctd_ascii_upper()", status)
    print(f"upper-case buffer: {c_string(upper_buffer)!r}")

    required_size = ffi.new("size_t *")
    status = lib.ctd_copy_string(
        b"copied through a caller-provided buffer",
        ffi.NULL,
        0,
        required_size,
    )
    show_status("ctd_copy_string() size query", status)
    print(f"required bytes including NUL: {required_size[0]}")

    copied_string = ffi.new("char[]", required_size[0])
    status = lib.ctd_copy_string(
        b"copied through a caller-provided buffer",
        copied_string,
        required_size[0],
        required_size,
    )
    show_status("ctd_copy_string() copy", status)
    print(f"copied string: {c_string(copied_string)!r}")
    # Pytest equivalent: assert ffi.string(copied_string) == expected_bytes
    assert ffi.string(copied_string) == b"copied through a caller-provided buffer"


def demo_structures_and_tagged_unions() -> None:
    # Recommended canonical pattern catalogue - 7. Structures and tagged unions.
    heading("Structures and fixed-size structure arrays")

    first = lib.ctd_point_make(2.0, 3.0)
    second = lib.ctd_point_make(-1.0, 4.0)
    combined = lib.ctd_point_add(first, second)

    print(f"first point: {point_tuple(first)}")
    print(f"second point: {point_tuple(second)}")
    print(f"ctd_point_add(): {point_tuple(combined)}")
    print(
        f"ctd_point_dot(): {lib.ctd_point_dot(ffi.addressof(first), ffi.addressof(second))}"
    )

    point = ffi.new("ctd_point *", {"x": 10.0, "y": 20.0})
    status = lib.ctd_point_translate(point, 1.5, -2.5)
    show_status("ctd_point_translate()", status)
    print(f"translated point: {point_tuple(point[0])}")

    record = ffi.new("ctd_record *")
    status = lib.ctd_record_initialize(record, 77, b"sample")
    show_status("ctd_record_initialize()", status)
    print(
        "record:",
        {
            "id": record.id,
            "name": c_string(record.name),
            "values": list(record.values),
        },
    )

    heading("Tagged union")

    integer_value = lib.ctd_value_from_i64(123456789)
    floating_value = lib.ctd_value_from_f64(3.25)
    converted = ffi.new("double *")

    status = lib.ctd_value_as_f64(ffi.addressof(integer_value), converted)
    show_status("ctd_value_as_f64(i64)", status)
    print(
        f"kind={integer_value.kind}, i64={integer_value.number.i64}, "
        f"converted={converted[0]}"
    )

    status = lib.ctd_value_as_f64(ffi.addressof(floating_value), converted)
    show_status("ctd_value_as_f64(f64)", status)
    print(
        f"kind={floating_value.kind}, f64={floating_value.number.f64}, "
        f"converted={converted[0]}"
    )

    config = lib.ctd_default_config()
    ranged_value = ffi.new("double *")
    status = lib.ctd_range_apply(config, 125.0, ranged_value)
    show_status("ctd_range_apply()", status)
    print(f"default-config clamped value: {ranged_value[0]}")

    described_values = ffi.new("int32_t[]", [4, 8, 15, 16, 23, 42])
    descriptor = ffi.new("ctd_descriptor *")
    status = lib.ctd_describe_i32(described_values, 6, descriptor)
    show_status("ctd_describe_i32()", status)
    descriptor_message = cast(bytes, ffi.string(descriptor.message)).decode("utf-8")
    descriptor_count = descriptor.count
    descriptor_values = list(ffi.unpack(descriptor.values, descriptor_count))
    print(f"descriptor: {descriptor_message!r}, values={descriptor_values}")

    static_descriptor = lib.ctd_static_descriptor()
    static_message = cast(bytes, ffi.string(static_descriptor.message)).decode("utf-8")
    static_count = static_descriptor.count
    static_values = list(ffi.unpack(static_descriptor.values, static_count))
    print(f"static descriptor: {static_message!r}, values={static_values}")
    # Pytest equivalent: assert descriptor_values == described_values
    assert descriptor_values == [4, 8, 15, 16, 23, 42]

    heading("Advanced callbacks and function pointers")

    user_data = ffi.new("int *", 10)

    def weighted_add(
        callback_left: int,
        callback_right: int,
        opaque: CffiValue,
    ) -> int:
        weight = ffi.cast("int *", opaque)[0]
        return int(callback_left + callback_right * weight)

    weighted_add_callback = ffi.callback("int(int, int, void *)")(weighted_add)
    callback_result = ffi.new("int *")
    status = lib.ctd_apply_callback(
        2,
        3,
        weighted_add_callback,
        user_data,
        callback_result,
    )
    show_status("ctd_apply_callback()", status)
    print(f"callback result: {callback_result[0]}")

    weighted_add_callback = ffi.callback("ctd_binary_callback")(weighted_add)
    callback_result = ffi.new("int *")
    status = lib.ctd_apply_callback(
        3,
        4,
        weighted_add_callback,
        user_data,
        callback_result,
    )
    show_status("ctd_apply_callback()", status)
    print(f"callback result: {callback_result[0]}")

    for selector in (
        lib.CTD_BINARY_OPERATION_ADD,
        lib.CTD_BINARY_OPERATION_MULTIPLY,
        99,
    ):
        operation = lib.ctd_get_binary_operation(selector)
        if operation == ffi.NULL:
            print(f"ctd_get_binary_operation({selector}): NULL")
        else:
            print(f"ctd_get_binary_operation({selector})(6, 7): {operation(6, 7)}")


def demo_opaque_handles_and_release() -> None:
    # Recommended canonical pattern catalogue - 8. Opaque handles and release.
    heading("Opaque counter handle")

    counter = lib.ctd_counter_create(100)
    if counter == ffi.NULL:
        raise MemoryError("ctd_counter_create() failed")

    counter_value = ffi.new("int *")

    try:
        status = lib.ctd_counter_get(counter, counter_value)
        show_status("ctd_counter_get()", status)
        print(f"value: {counter_value[0]}")

        status = lib.ctd_counter_add(counter, 23, counter_value)
        show_status("ctd_counter_add()", status)
        print(f"value: {counter_value[0]}")
    finally:
        lib.ctd_free(counter)

    accumulator = lib.ctd_accumulator_create(2)
    if accumulator == ffi.NULL:
        raise MemoryError("ctd_accumulator_create() failed")
    accumulated = ffi.new("int64_t *")
    try:
        show_status("ctd_accumulator_add(20)", lib.ctd_accumulator_add(accumulator, 20))
        show_status("ctd_accumulator_add(22)", lib.ctd_accumulator_add(accumulator, 22))
        show_status(
            "ctd_accumulator_get()", lib.ctd_accumulator_get(accumulator, accumulated)
        )
        print(f"accumulated value: {accumulated[0]}")
        # Pytest equivalent: assert accumulated[0] == 42
        assert accumulated[0] == 42
    finally:
        lib.ctd_accumulator_destroy(accumulator)

    heading("Explicit NULL-safe release")

    lib.ctd_free(ffi.NULL)
    print("ctd_free(NULL): completed")

    lib.ctd_globals_reset()
    print(
        "mutable globals restored:",
        {
            "counter": lib.ctd_global_counter,
            "last_status": lib.ctd_global_last_status,
            "scale": lib.ctd_global_scale,
        },
    )


def main() -> int:
    demo_globals_and_status_values()
    demo_scalar_and_value_operations()
    demo_scalar_pointer_operations()
    demo_typed_arrays()
    demo_byte_buffers()
    demo_strings()
    demo_structures_and_tagged_unions()
    demo_opaque_handles_and_release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
