/*
** ctd_api.h
*/

#ifndef CTD_API_H
#define CTD_API_H

/*
** This declaration catalogue is included by ctd.h, which supplies
** CTD_TEST_API and CTD_TEST_DATA_API, and is not an independent C client header.
**



** Canonical API pattern catalogue:
**
** The nine contract families below are ordered from value-only calls through
** progressively more explicit pointer and lifetime management. A pointer
** profile records DIRECTION, SHAPE, NULLABILITY, RETENTION, OWNERSHIP, and the
** UNIT used by each associated size. "Not retained" means that CTD does not
** keep the pointer after the call returns.
**
** Shared CFFI ownership rules:
** - Memory created by ffi.new() is caller-owned. Keep its owning cdata alive
**   for every call that uses it; CTD never frees or retains that memory.
** - A borrowed C return remains library-owned, must not be passed to
**   ctd_free(), and is valid only for the lifetime stated by its profile.
** - An owned C return is caller-owned after a successful call and must be
**   released exactly once with the matching CTD release function.
** - OUT and INOUT storage is supplied and owned by the caller unless the
**   declaration explicitly describes an owned return. Size-query calls may
**   allow NULL output storage while still requiring a non-NULL size pointer.
** - Allocators must not be mixed: ffi.new() memory is released by Python/CFFI;
**   CTD allocations are released only by ctd_free().
** - Unless a declaration says otherwise, a status-returning function leaves
**   every caller-provided OUT or INOUT object unchanged on failure. Size-query
**   functions are the exception: their required count/size output is set once
**   the input has been validated, including on CTD_ERROR_CAPACITY.
**
** Catalogue audit (the 25 requested patterns, deliberately mapped to focused
** functions rather than one API per line):
**  1 ctd_add; 2 ctd_hypot_squared; 3 ctd_divide; 4 ctd_get_magic;
**  5 ctd_increment; 6 ctd_utf8_byte_size; 7 ctd_checksum_bytes;
**  8 ctd_select_static_string; 9 ctd_alloc_greeting; 10 ctd_copy_string;
** 11 ctd_sum_i32; 12 ctd_reverse_i32/ctd_scale_i32;
** 13,24,25 ctd_make_sequence_i32; 14 ctd_borrow_sequence_i32;
** 15 ctd_alloc_sequence_i32; 16,17 ctd_point_add; 18 ctd_point_dot;
** 19 ctd_point_translate; 20 ctd_compute_stats_i32;
** 21 ctd_default_config; 22 ctd_accumulator_create/add/get/destroy;
** 23 ctd_utf8_byte_size. ctd_static_descriptor is the descriptor-structure
** pattern whose borrowed fields have separate lifetime contracts.
*/

/*
** Error codes.
*/
typedef enum ctd_status {
    CTD_OK = 0,
    CTD_ERROR_NULL = 1,
    CTD_ERROR_RANGE = 2,
    CTD_ERROR_CAPACITY = 3,
    CTD_ERROR_ALLOCATION = 4,
    CTD_ERROR_DIVIDE_BY_ZERO = 5
} ctd_status;

/*
** Advanced declarations for CFFI introspection examples. These types enrich
** the declaration model; graph traversal and Python callback invocation are
** deliberately outside the canonical runtime profile.
*/
typedef union ctd_number {
    int64_t i64;
    double f64;
} ctd_number;

typedef int (*ctd_binary_callback)(int left, int right, void *user_data);
/* Returned values are borrowed library-owned function pointers. */
typedef int (*ctd_binary_operation)(int left, int right);

typedef enum ctd_binary_operation_kind {
    CTD_BINARY_OPERATION_ADD = 0,
    CTD_BINARY_OPERATION_MULTIPLY = 1
} ctd_binary_operation_kind;

typedef int (*ctd_value_predicate)(const ctd_number *value, void *user_data);
typedef void (*ctd_message_callback)(const char *message, size_t length);

typedef struct ctd_counter ctd_counter;
typedef struct ctd_accumulator ctd_accumulator;
typedef struct ctd_graph ctd_graph;

typedef struct ctd_node {
    int32_t value;
    struct ctd_node *next;
    struct ctd_node *child;
} ctd_node;

/* Primary structure and enum catalogue. */
typedef struct ctd_point {
    double x;
    double y;
} ctd_point;

/*
** A structure populated through an output pointer.
*/
typedef struct ctd_stats {
    size_t count;
    int32_t minimum;
    int32_t maximum;
    int64_t sum;
    double mean;
} ctd_stats;

/*
** A structure containing fixed-size arrays.
*/
typedef struct ctd_record {
    int32_t id;
    char name[16];
    double values[3];
} ctd_record;

typedef enum ctd_number_kind {
    CTD_NUMBER_I64 = 1,
    CTD_NUMBER_F64 = 2
} ctd_number_kind;

typedef struct ctd_value {
    ctd_number_kind kind;
    ctd_number number;
} ctd_value;

typedef struct ctd_range {
    double minimum;
    double maximum;
} ctd_range;

typedef enum ctd_range_policy {
    CTD_RANGE_REJECT = 0,
    CTD_RANGE_CLAMP = 1
} ctd_range_policy;

typedef struct ctd_config {
    ctd_range range;
    ctd_range_policy policy;
} ctd_config;

typedef struct ctd_descriptor {
    const char *message;
    const int32_t *values;
    size_t count;
} ctd_descriptor;

#ifndef SQLITE_CORE /* Drop declaration of globals when amalgmated */

/* Recommended canonical pattern catalogue - 1. Globals and status values. */
CTD_TEST_DATA_API int ctd_global_counter;
CTD_TEST_DATA_API ctd_status ctd_global_last_status;
CTD_TEST_DATA_API double ctd_global_scale;
CTD_TEST_DATA_API ctd_point ctd_global_cur_point;

/*
** Do not emit declarations for static const symbols in internal-linkage mode.
** Their initialized definitions in ctd.c are the declarations/definitions for
** that mode; uninitialized file-scope static const declarations trigger MSVC
** warnings and are unnecessary.
*/
#if defined(CTD_TEST) || defined(CTD_BUILD_STATIC_LIB)

CTD_TEST_DATA_API const size_t ctd_max_supported_point_count;
CTD_TEST_DATA_API const double ctd_numeric_epsilon;
CTD_TEST_DATA_API const char ctd_library_name[4];
CTD_TEST_DATA_API const ctd_point ctd_origin_point;

#endif

#endif /* SQLITE_CORE */

/* RETURN: OUT STRING; non-NULL; borrowed, library-owned, static lifetime. */
CTD_TEST_API const char *ctd_version(void);
/* RETURN: OUT STRING; non-NULL; borrowed, library-owned, static lifetime. */
CTD_TEST_API const char *ctd_status_name(ctd_status status);
CTD_TEST_API int ctd_global_counter_increment(void);
CTD_TEST_API void ctd_global_counter_reset(void);
CTD_TEST_API void ctd_globals_reset(void);

/* Recommended canonical pattern catalogue - 2. Scalar and value operations. */
/* Saturates at INT_MIN/INT_MAX when the mathematical sum is out of range. */
CTD_TEST_API int ctd_add(int a, int b);
/* Saturates at INT32_MAX when value is INT32_MIN. */
CTD_TEST_API int32_t ctd_negate_i32(int32_t value);
CTD_TEST_API uint64_t ctd_add_u64(uint64_t a, uint64_t b);
/*
** Computes x*x + y*y using ordinary C double arithmetic. NaNs and infinities
** propagate according to the implementation's floating-point environment;
** finite inputs may overflow to positive infinity.
*/
CTD_TEST_API double ctd_hypot_squared(double x, double y);

/* result: OUT SCALAR; non-NULL; not retained; caller-owned; no size unit. */
CTD_TEST_API ctd_status ctd_divide(
    double numerator,
    double denominator,
    double *result
);

/* Recommended canonical pattern catalogue - 3. Scalar pointer operations. */
/* result: OUT SCALAR; non-NULL; not retained; caller-owned; no size unit. */
CTD_TEST_API ctd_status ctd_get_magic(int32_t *result);
/* value: INOUT SCALAR; non-NULL; not retained; caller-owned; no size unit. */
CTD_TEST_API ctd_status ctd_increment(int32_t *value);
/* a, b: INOUT SCALAR; non-NULL; not retained; caller-owned; no size unit. */
CTD_TEST_API ctd_status ctd_swap_i32(int32_t *a, int32_t *b);

/* Recommended canonical pattern catalogue - 4. Typed arrays. */
/*
** values: IN ARRAY; NULL only when count is zero; not retained; caller-owned;
** count unit: int32_t elements.
** result: OUT SCALAR; non-NULL; not retained; caller-owned; no size unit.
*/
CTD_TEST_API ctd_status ctd_sum_i32(
    const int32_t *values, 
    size_t count, 
    int64_t *result
);

/* values: INOUT ARRAY; NULL only when count is zero; not retained;
** caller-owned; count unit: int32_t elements. */
CTD_TEST_API ctd_status ctd_reverse_i32(int32_t *values, size_t count);

/* values: INOUT ARRAY; NULL only when count is zero; unchanged on failure;
** caller-owned; count unit: int32_t elements. */
CTD_TEST_API ctd_status ctd_scale_i32(int32_t *values, size_t count, int32_t factor);

/*
** values: IN ARRAY; non-NULL; not retained; caller-owned; count unit: int32_t
** elements (count must be greater than zero).
** result: OUT STRUCT; non-NULL; not retained; caller-owned; no size unit.
*/
CTD_TEST_API ctd_status ctd_compute_stats_i32(
    const int32_t *values,
    size_t count,
    ctd_stats *result
);

/*
** buffer: OUT ARRAY; NULL for a size query or zero count; not retained;
** caller-owned; capacity unit: int32_t elements.
** required_count: OUT SCALAR; non-NULL; not retained; caller-owned; value unit:
** int32_t elements. count unit: int32_t elements.
*/
CTD_TEST_API ctd_status ctd_make_sequence_i32(
    int32_t start,
    size_t count,
    int32_t *buffer,
    size_t capacity,
    size_t *required_count
);

/* RETURN: OUT ARRAY; NULL on zero count or failure; not retained; caller-owned
** after return; count unit: int32_t elements; release with ctd_free(). */
CTD_TEST_API int32_t *ctd_alloc_sequence_i32(int32_t start, size_t count);

/* count: OUT SCALAR; non-NULL; receives an element count.
** RETURN: OUT ARRAY; non-NULL; borrowed library-owned static lifetime; the
** returned int32_t elements must not be modified or freed. */
CTD_TEST_API const int32_t *ctd_borrow_sequence_i32(size_t *count);

/* Recommended canonical pattern catalogue - 5. Byte buffers. */
/*
** source: IN BUFFER; NULL only when source_count is zero; not retained;
** caller-owned; source_count unit: bytes.
** destination: OUT BUFFER; NULL for a size query or zero source_count; not
** retained; caller-owned; destination_capacity unit: bytes.
** required_count: OUT SCALAR; non-NULL; not retained; caller-owned; value
** unit: bytes.
*/
CTD_TEST_API ctd_status ctd_copy_bytes(
    const uint8_t *source,
    size_t source_count,
    uint8_t *destination,
    size_t destination_capacity,
    size_t *required_count
);

/* buffer: INOUT BUFFER; NULL only when count is zero; not retained;
** caller-owned; count unit: bytes. */
CTD_TEST_API ctd_status ctd_xor_bytes(uint8_t *buffer, size_t count, uint8_t mask);

/* bytes: IN BUFFER; NULL only when length is zero; not retained; caller-owned;
** length unit: bytes. result: OUT SCALAR; non-NULL and unchanged on failure;
** value is the sum of all bytes modulo 2^32. */
CTD_TEST_API ctd_status ctd_checksum_bytes(
    const uint8_t *bytes,
    size_t length,
    uint32_t *result
);

/* Recommended canonical pattern catalogue - 6. Strings. */
/* text: IN UTF-8 STRING; nullable; not retained; caller-owned; size inferred
** by NUL. RETURN is the number of encoded bytes before NUL, not Unicode code
** points. Embedded zero bytes therefore require an explicit-length byte API. */
CTD_TEST_API size_t ctd_utf8_byte_size(const char *text);
/* RETURN: OUT STRING; nullable; not retained; borrowed library-owned static
** memory; size inferred by NUL; must not be freed. */
CTD_TEST_API const char *ctd_select_static_string(int selector);
/* name: IN STRING; non-NULL; not retained; caller-owned; size inferred by NUL.
** RETURN: OUT STRING; NULL on failure; not retained; caller-owned after return;
** size inferred by NUL; release with ctd_free(). */
CTD_TEST_API char *ctd_alloc_greeting(const char *name);

/* buffer: INOUT STRING; non-NULL; not retained; caller-owned; capacity unit:
** bytes including the terminating NUL. */
CTD_TEST_API ctd_status ctd_ascii_upper(char *buffer, size_t capacity);

/*
** source: IN STRING; non-NULL; not retained; caller-owned; size inferred by NUL.
** destination: OUT STRING; NULL for a size query; not retained; caller-owned;
** destination_capacity unit: bytes including the terminating NUL.
** required_size: OUT SCALAR; non-NULL; not retained; caller-owned; value unit:
** bytes including the terminating NUL.
*/
CTD_TEST_API ctd_status ctd_copy_string(
    const char *source,
    char *destination,
    size_t destination_capacity,
    size_t *required_size
);

/* Recommended canonical pattern catalogue - 7. Structures and tagged unions. */
CTD_TEST_API ctd_point ctd_point_make(double x, double y);
CTD_TEST_API ctd_point ctd_point_add(ctd_point a, ctd_point b);
/* a, b: IN STRUCT; non-NULL; not retained; caller-owned; no size unit. */
CTD_TEST_API double ctd_point_dot(const ctd_point *a, const ctd_point *b);
/* point: INOUT STRUCT; non-NULL; not retained; caller-owned; no size unit. */
CTD_TEST_API ctd_status ctd_point_translate(ctd_point *point, double dx, double dy);

/* record: OUT STRUCT; non-NULL; not retained; caller-owned; no size unit.
** name: IN STRING; non-NULL; not retained; caller-owned; size inferred by NUL. */
CTD_TEST_API ctd_status ctd_record_initialize(
    ctd_record *record,
    int32_t id,
    const char *name
);

CTD_TEST_API ctd_value ctd_value_from_i64(int64_t value);
CTD_TEST_API ctd_value ctd_value_from_f64(double value);
/* value: IN STRUCT; non-NULL; not retained; caller-owned; no size unit.
** result: OUT SCALAR; non-NULL; not retained; caller-owned; no size unit. */
CTD_TEST_API ctd_status ctd_value_as_f64(const ctd_value *value, double *result);

/* RETURN: OUT STRUCT; non-NULL; borrowed library-owned static lifetime. */
CTD_TEST_API const ctd_config *ctd_default_config(void);
/* config: IN STRUCT; non-NULL; not retained; caller-owned; no size unit.
** result: OUT SCALAR; non-NULL; not retained; caller-owned; no size unit. */
CTD_TEST_API ctd_status ctd_range_apply(
    const ctd_config *config,
    double value,
    double *result
);
/* values: IN ARRAY; NULL only when count is zero; borrowed by result;
** caller-owned; count unit: int32_t elements. Keep the owning cdata alive for
** every access through result->values.
** result: OUT STRUCT; non-NULL; its message is borrowed static storage and its
** values member aliases the input while that input remains alive. */
CTD_TEST_API ctd_status ctd_describe_i32(
    const int32_t *values,
    size_t count,
    ctd_descriptor *result
);

/* RETURN: OUT DESCRIPTOR STRUCT; non-NULL; borrowed library-owned static
** lifetime. The structure, message, and values fields are all static and
** read-only; count is measured in int32_t elements. Nothing may be freed. */
CTD_TEST_API const ctd_descriptor *ctd_static_descriptor(void);

/* Advanced callback and returned-function-pointer examples. */
/* callback: IN OPAQUE callable pointer; non-NULL; not retained; caller-owned;
** no size unit. user_data: IN OPAQUE; nullable; not retained; caller-owned; no
** size unit. result: OUT SCALAR; non-NULL; not retained; caller-owned; no size
** unit. Keep both callback and user_data cdata alive for the call. */
CTD_TEST_API ctd_status ctd_apply_callback(
    int left,
    int right,
    ctd_binary_callback callback,
    void *user_data,
    int *result
);

/* RETURN: OUT OPAQUE function pointer; nullable; borrowed library-owned static
** code; no size unit; must not be freed. */
CTD_TEST_API ctd_binary_operation ctd_get_binary_operation(
    ctd_binary_operation_kind operation_kind
);

/* Recommended canonical pattern catalogue - 8. Opaque handles and release. */
/* RETURN: OUT OPAQUE; NULL on failure; retained as handle state; caller-owned
** after return; no size unit; release with ctd_free(). The allocation contains
** no nested resources and requires no type-specific teardown. */
CTD_TEST_API ctd_counter *ctd_counter_create(int initial_value);
/* counter: IN OPAQUE; non-NULL; retained as handle state; caller-owned; no size
** unit. result: OUT SCALAR; non-NULL; not retained; caller-owned; no size unit. */
CTD_TEST_API ctd_status ctd_counter_get(const ctd_counter *counter, int *result);
/* counter: INOUT OPAQUE; non-NULL; retained as handle state; caller-owned; no
** size unit. result: OUT SCALAR; non-NULL; not retained; caller-owned; no size
** unit. */
CTD_TEST_API ctd_status ctd_counter_add(ctd_counter *counter, int amount, int *result);

/* A genuinely opaque lifecycle object with a type-specific release operation.
** Its representation and owned state are private to ctd.c. */
/* RETURN: OUT OPAQUE; NULL on failure; retained as handle state; caller-owned
** after return; no size unit; release with ctd_accumulator_destroy(). Do not
** pass this handle to ctd_free() because it owns nested allocated state. */
CTD_TEST_API ctd_accumulator *ctd_accumulator_create(size_t capacity);
CTD_TEST_API ctd_status ctd_accumulator_add(
    ctd_accumulator *accumulator,
    int32_t value
);
CTD_TEST_API ctd_status ctd_accumulator_get(
    const ctd_accumulator *accumulator,
    int64_t *result
);
CTD_TEST_API void ctd_accumulator_destroy(ctd_accumulator *accumulator);

/* pointer: IN OPAQUE allocation; nullable; consumed/released, not retained;
** caller-owned before call and originally allocated by CTD; no size unit. Only
** pass pointers documented for release with ctd_free(). The pointer is invalid
** after this call. */
CTD_TEST_API void ctd_free(void *pointer);

#endif /* CTD_API_H */
