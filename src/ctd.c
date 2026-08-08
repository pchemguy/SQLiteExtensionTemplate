/*
** ctd.c
**
** Standalone C99 DLL fixture for exploring Python CFFI.
*/

#include "ctd.h"

#include <limits.h>
#include <stdlib.h>
#include <string.h>

/* The counter layout is private; ctd_api.h exposes only its typedef. */
struct ctd_counter {
    int value;
};

struct ctd_accumulator {
    int32_t *values;
    size_t count;
    size_t capacity;
    int64_t total;
};

/* Recommended canonical pattern catalogue - 1. Globals and status values. */
CTD_TEST_DATA_DEF int ctd_global_counter = 0;
CTD_TEST_DATA_DEF ctd_status ctd_global_last_status = CTD_OK;
CTD_TEST_DATA_DEF double ctd_global_scale = 1.0;
CTD_TEST_DATA_DEF ctd_point ctd_global_cur_point = {0.0, 0.0};

CTD_TEST_DATA_DEF const size_t ctd_max_supported_point_count = 1024;
CTD_TEST_DATA_DEF const double ctd_numeric_epsilon = 1.0e-12;
CTD_TEST_DATA_DEF const char ctd_library_name[] = "CTD";
CTD_TEST_DATA_DEF const ctd_point ctd_origin_point = {0.0, 0.0};

CTD_TEST_API const char *ctd_version(void) {
    return "ctd 1.0";
}

CTD_TEST_API const char *ctd_status_name(ctd_status status) {
    switch (status) {
        case CTD_OK:
            return "CTD_OK";
        case CTD_ERROR_NULL:
            return "CTD_ERROR_NULL";
        case CTD_ERROR_RANGE:
            return "CTD_ERROR_RANGE";
        case CTD_ERROR_CAPACITY:
            return "CTD_ERROR_CAPACITY";
        case CTD_ERROR_ALLOCATION:
            return "CTD_ERROR_ALLOCATION";
        case CTD_ERROR_DIVIDE_BY_ZERO:
            return "CTD_ERROR_DIVIDE_BY_ZERO";
        default:
            return "CTD_ERROR_UNKNOWN";
    }
}

CTD_TEST_API int ctd_global_counter_increment(void) {
    if (ctd_global_counter == INT_MAX) {
        return ctd_global_counter;
    }
    ctd_global_counter += 1;
    return ctd_global_counter;
}

CTD_TEST_API void ctd_global_counter_reset(void) {
    ctd_global_counter = 0;
}

CTD_TEST_API void ctd_globals_reset(void) {
    ctd_global_counter = 0;
    ctd_global_last_status = CTD_OK;
    ctd_global_scale = 1.0;
    ctd_global_cur_point = (ctd_point){0.0, 0.0};
}

/* Recommended canonical pattern catalogue - 2. Scalar and value operations. */
CTD_TEST_API int ctd_add(int a, int b) {
    if (b > 0 && a > INT_MAX - b) {
        return INT_MAX;
    }
    if (b < 0 && a < INT_MIN - b) {
        return INT_MIN;
    }
    return a + b;
}

CTD_TEST_API int32_t ctd_negate_i32(int32_t value) {
    if (value == INT32_MIN) {
        return INT32_MAX;
    }
    return -value;
}

CTD_TEST_API uint64_t ctd_add_u64(uint64_t a, uint64_t b) {
    return a + b;
}

CTD_TEST_API double ctd_hypot_squared(double x, double y) {
    return x * x + y * y;
}

CTD_TEST_API ctd_status ctd_divide(
    double numerator, 
    double denominator, 
    double *result
) {
    if (result == NULL) {
        return CTD_ERROR_NULL;
    }

    if (denominator == 0.0) {
        return CTD_ERROR_DIVIDE_BY_ZERO;
    }

    *result = numerator / denominator;
    return CTD_OK;
}

/* Recommended canonical pattern catalogue - 3. Scalar pointer operations. */
CTD_TEST_API ctd_status ctd_get_magic(int32_t *result) {
    if (result == NULL) {
        return CTD_ERROR_NULL;
    }

    *result = INT32_C(123456);
    return CTD_OK;
}

CTD_TEST_API ctd_status ctd_increment(int32_t *value) {
    if (value == NULL) {
        return CTD_ERROR_NULL;
    }

    if (*value == INT32_MAX) {
        return CTD_ERROR_RANGE;
    }

    *value += 1;
    return CTD_OK;
}

CTD_TEST_API ctd_status ctd_swap_i32(int32_t *a, int32_t *b) {
    int32_t temporary;

    if (a == NULL || b == NULL) {
        return CTD_ERROR_NULL;
    }

    temporary = *a;
    *a = *b;
    *b = temporary;

    return CTD_OK;
}

/* Recommended canonical pattern catalogue - 4. Typed arrays. */
CTD_TEST_API ctd_status ctd_sum_i32(
    const int32_t *values,
    size_t count,
    int64_t *result
) {
    size_t index;
    int64_t sum = 0;

    if (result == NULL) {
        return CTD_ERROR_NULL;
    }

    if (values == NULL && count != 0) {
        return CTD_ERROR_NULL;
    }

    for (index = 0; index < count; ++index) {
        if ((values[index] > 0 && sum > INT64_MAX - values[index]) ||
            (values[index] < 0 && sum < INT64_MIN - values[index])) {
            return CTD_ERROR_RANGE;
        }
        sum += values[index];
    }

    *result = sum;
    return CTD_OK;
}

CTD_TEST_API ctd_status ctd_reverse_i32(int32_t *values, size_t count) {
    size_t left;
    size_t right;
    int32_t temporary;

    if (values == NULL && count != 0) {
        return CTD_ERROR_NULL;
    }

    if (count < 2) {
        return CTD_OK;
    }

    left = 0;
    right = count - 1;

    while (left < right) {
        temporary = values[left];
        values[left] = values[right];
        values[right] = temporary;

        ++left;
        --right;
    }

    return CTD_OK;
}

CTD_TEST_API ctd_status ctd_scale_i32(int32_t *values, size_t count, int32_t factor) {
    size_t index;

    if (values == NULL && count != 0) {
        return CTD_ERROR_NULL;
    }

    for (index = 0; index < count; ++index) {
        int64_t scaled = (int64_t)values[index] * (int64_t)factor;
        if (scaled < INT32_MIN || scaled > INT32_MAX) {
            return CTD_ERROR_RANGE;
        }
    }

    for (index = 0; index < count; ++index) {
        values[index] = (int32_t)((int64_t)values[index] * (int64_t)factor);
    }
    return CTD_OK;
}

CTD_TEST_API ctd_status ctd_compute_stats_i32(
    const int32_t *values,
    size_t count,
    ctd_stats *result
) {
    size_t index;
    int64_t sum;
    int32_t minimum;
    int32_t maximum;

    if (result == NULL) {
        return CTD_ERROR_NULL;
    }

    if (values == NULL) {
        return CTD_ERROR_NULL;
    }

    if (count == 0) {
        return CTD_ERROR_RANGE;
    }

    minimum = values[0];
    maximum = values[0];
    sum = values[0];

    for (index = 1; index < count; ++index) {
        if (values[index] < minimum) {
            minimum = values[index];
        }

        if (values[index] > maximum) {
            maximum = values[index];
        }

        if ((values[index] > 0 && sum > INT64_MAX - values[index]) ||
            (values[index] < 0 && sum < INT64_MIN - values[index])) {
            return CTD_ERROR_RANGE;
        }
        sum += values[index];
    }

    result->count = count;
    result->minimum = minimum;
    result->maximum = maximum;
    result->sum = sum;
    result->mean = (double)sum / (double)count;

    return CTD_OK;
}

CTD_TEST_API ctd_status ctd_make_sequence_i32(
    int32_t start,
    size_t count,
    int32_t *buffer,
    size_t capacity,
    size_t *required_count
) {
    size_t index;

    if (required_count == NULL) {
        return CTD_ERROR_NULL;
    }

    if (count > 0 &&
        (count - 1 > (size_t)INT32_MAX ||
         start > INT32_MAX - (int32_t)(count - 1))) {
        return CTD_ERROR_RANGE;
    }

    *required_count = count;

    if (count == 0) {
        return CTD_OK;
    }

    if (buffer == NULL) {
        return CTD_ERROR_CAPACITY;
    }

    if (capacity < count) {
        return CTD_ERROR_CAPACITY;
    }

    for (index = 0; index < count; ++index) {
        buffer[index] = start + (int32_t)index;
    }

    return CTD_OK;
}

CTD_TEST_API int32_t *ctd_alloc_sequence_i32(int32_t start, size_t count) {
    int32_t *result;
    size_t index;

    if (count == 0) {
        return NULL;
    }

    if (count > SIZE_MAX / sizeof(*result)) {
        return NULL;
    }

    if (count - 1 > (size_t)INT32_MAX ||
        start > INT32_MAX - (int32_t)(count - 1)) {
        return NULL;
    }

    result = (int32_t *)malloc(count * sizeof(*result));

    if (result == NULL) {
        return NULL;
    }

    for (index = 0; index < count; ++index) {
        result[index] = start + (int32_t)index;
    }

    return result;
}

CTD_TEST_API const int32_t *ctd_borrow_sequence_i32(size_t *count) {
    static const int32_t values[] = {2, 3, 5, 7, 11};

    if (count == NULL) {
        return NULL;
    }
    *count = sizeof(values) / sizeof(values[0]);
    return values;
}

/* Recommended canonical pattern catalogue - 5. Byte buffers. */
CTD_TEST_API ctd_status ctd_copy_bytes(
    const uint8_t *source,
    size_t source_count,
    uint8_t *destination,
    size_t destination_capacity,
    size_t *required_count
) {
    if (required_count == NULL) {
        return CTD_ERROR_NULL;
    }

    if (source == NULL && source_count != 0) {
        return CTD_ERROR_NULL;
    }

    *required_count = source_count;

    if (source_count == 0) {
        return CTD_OK;
    }

    if (destination == NULL || destination_capacity < source_count) {
        return CTD_ERROR_CAPACITY;
    }

    memmove(destination, source, source_count);
    return CTD_OK;
}

CTD_TEST_API ctd_status ctd_xor_bytes(uint8_t *buffer, size_t count, uint8_t mask) {
    size_t index;

    if (buffer == NULL && count != 0) {
        return CTD_ERROR_NULL;
    }

    for (index = 0; index < count; ++index) {
        buffer[index] ^= mask;
    }

    return CTD_OK;
}

CTD_TEST_API ctd_status ctd_checksum_bytes(
    const uint8_t *bytes,
    size_t length,
    uint32_t *result
) {
    size_t index;
    uint32_t checksum = 0;

    if (result == NULL || (bytes == NULL && length != 0)) {
        return CTD_ERROR_NULL;
    }
    for (index = 0; index < length; ++index) {
        checksum += bytes[index];
    }
    *result = checksum;
    return CTD_OK;
}

/* Recommended canonical pattern catalogue - 6. Strings. */
CTD_TEST_API size_t ctd_utf8_byte_size(const char *text) {
    if (text == NULL) {
        return 0;
    }

    return strlen(text);
}

CTD_TEST_API const char *ctd_select_static_string(int selector) {
    switch (selector) {
        case 0:
            return "zero";
        case 1:
            return "one";
        case 2:
            return "";
        default:
            return NULL;
    }
}

CTD_TEST_API char *ctd_alloc_greeting(const char *name) {
    static const char prefix[] = "Hello, ";
    static const char suffix[] = "!";
    size_t prefix_size = sizeof(prefix) - 1;
    size_t suffix_size = sizeof(suffix) - 1;
    size_t name_size;
    size_t total_size;
    char *result;

    if (name == NULL) {
        return NULL;
    }

    name_size = strlen(name);

    if (name_size > SIZE_MAX - prefix_size - suffix_size - 1) {
        return NULL;
    }

    total_size = prefix_size + name_size + suffix_size + 1;
    result = (char *)malloc(total_size);

    if (result == NULL) {
        return NULL;
    }

    memmove(result, prefix, prefix_size);
    memmove(result + prefix_size, name, name_size);
    memmove(result + prefix_size + name_size, suffix, suffix_size);
    result[total_size - 1] = '\0';

    return result;
}

CTD_TEST_API ctd_status ctd_ascii_upper(char *buffer, size_t capacity) {
    size_t index;
    char *terminator;

    if (buffer == NULL) {
        return CTD_ERROR_NULL;
    }

    terminator = (char *)memchr(buffer, '\0', capacity);
    if (terminator == NULL) {
        return CTD_ERROR_CAPACITY;
    }

    for (index = 0; index < (size_t)(terminator - buffer); ++index) {
        unsigned char character = (unsigned char)buffer[index];

        if (character >= 'a' && character <= 'z') {
            buffer[index] = (char)(character - 'a' + 'A');
        }
    }

    return CTD_OK;
}

CTD_TEST_API ctd_status ctd_copy_string(
    const char *source,
    char *destination,
    size_t destination_capacity,
    size_t *required_size
) {
    size_t size;

    if (source == NULL || required_size == NULL) {
        return CTD_ERROR_NULL;
    }

    size = strlen(source);
    if (size == SIZE_MAX) {
        return CTD_ERROR_RANGE;
    }
    size += 1;
    *required_size = size;

    if (destination == NULL || destination_capacity < size) {
        return CTD_ERROR_CAPACITY;
    }

    memmove(destination, source, size);
    return CTD_OK;
}

/* Recommended canonical pattern catalogue - 7. Structures and tagged unions. */
CTD_TEST_API ctd_point ctd_point_make(double x, double y) {
    ctd_point result;

    result.x = x;
    result.y = y;

    return result;
}

CTD_TEST_API ctd_point ctd_point_add(ctd_point a, ctd_point b) {
    ctd_point result;

    result.x = a.x + b.x;
    result.y = a.y + b.y;

    return result;
}

CTD_TEST_API double ctd_point_dot(const ctd_point *a, const ctd_point *b) {
    return a->x * b->x + a->y * b->y;
}

CTD_TEST_API ctd_status ctd_point_translate(ctd_point *point, double dx, double dy) {
    if (point == NULL) {
        return CTD_ERROR_NULL;
    }

    point->x += dx;
    point->y += dy;

    return CTD_OK;
}

CTD_TEST_API ctd_status ctd_record_initialize(
    ctd_record *record,
    int32_t id,
    const char *name
) {
    size_t name_size;

    if (record == NULL || name == NULL) {
        return CTD_ERROR_NULL;
    }

    name_size = strlen(name);

    if (name_size >= sizeof(record->name)) {
        return CTD_ERROR_CAPACITY;
    }

    record->id = id;

    memset(record->name, 0, sizeof(record->name));
    memmove(record->name, name, name_size);

    record->values[0] = 1.0;
    record->values[1] = 2.0;
    record->values[2] = 3.0;

    return CTD_OK;
}

CTD_TEST_API ctd_value ctd_value_from_i64(int64_t value) {
    ctd_value result;

    result.kind = CTD_NUMBER_I64;
    result.number.i64 = value;

    return result;
}

CTD_TEST_API ctd_value ctd_value_from_f64(double value) {
    ctd_value result;

    result.kind = CTD_NUMBER_F64;
    result.number.f64 = value;

    return result;
}

CTD_TEST_API ctd_status ctd_value_as_f64(const ctd_value *value, double *result) {
    if (value == NULL || result == NULL) {
        return CTD_ERROR_NULL;
    }

    switch (value->kind) {
        case CTD_NUMBER_I64:
            *result = (double)value->number.i64;
            return CTD_OK;

        case CTD_NUMBER_F64:
            *result = value->number.f64;
            return CTD_OK;

        default:
            return CTD_ERROR_RANGE;
    }
}

CTD_TEST_API const ctd_config *ctd_default_config(void) {
    static const ctd_config config = {{0.0, 100.0}, CTD_RANGE_CLAMP};

    return &config;
}

CTD_TEST_API ctd_status ctd_range_apply(
    const ctd_config *config,
    double value,
    double *result
) {
    if (config == NULL || result == NULL) {
        return CTD_ERROR_NULL;
    }

    if (config->range.minimum > config->range.maximum) {
        return CTD_ERROR_RANGE;
    }

    if (config->policy != CTD_RANGE_REJECT && config->policy != CTD_RANGE_CLAMP) {
        return CTD_ERROR_RANGE;
    }

    if (value < config->range.minimum || value > config->range.maximum) {
        if (config->policy == CTD_RANGE_REJECT) {
            return CTD_ERROR_RANGE;
        }
        value = value < config->range.minimum
            ? config->range.minimum
            : config->range.maximum;
    }

    *result = value;
    return CTD_OK;
}

CTD_TEST_API ctd_status ctd_describe_i32(
    const int32_t *values,
    size_t count,
    ctd_descriptor *result
) {
    if (result == NULL || (values == NULL && count != 0)) {
        return CTD_ERROR_NULL;
    }

    result->message = count == 0 ? "empty sequence" : "integer sequence";
    result->values = values;
    result->count = count;
    return CTD_OK;
}

CTD_TEST_API const ctd_descriptor *ctd_static_descriptor(void) {
    static const int32_t values[] = {8, 13, 21};
    static const char message[] = "static Fibonacci descriptor";
    static const ctd_descriptor descriptor = {
        message,
        values,
        sizeof(values) / sizeof(values[0])
    };

    return &descriptor;
}

/* Advanced callback and returned-function-pointer examples. */
static int binary_operation_add(int left, int right) {
    return ctd_add(left, right);
}

static int binary_operation_multiply(int left, int right) {
    int64_t product = (int64_t)left * (int64_t)right;

    if (product > INT_MAX) {
        return INT_MAX;
    }
    if (product < INT_MIN) {
        return INT_MIN;
    }
    return (int)product;
}

CTD_TEST_API ctd_status ctd_apply_callback(
    int left,
    int right,
    ctd_binary_callback callback,
    void *user_data,
    int *result
) {
    if (callback == NULL || result == NULL) {
        return CTD_ERROR_NULL;
    }

    *result = callback(left, right, user_data);
    return CTD_OK;
}

CTD_TEST_API ctd_binary_operation ctd_get_binary_operation(
    ctd_binary_operation_kind operation_kind
) {
    switch (operation_kind) {
        case CTD_BINARY_OPERATION_ADD:
            return binary_operation_add;
        case CTD_BINARY_OPERATION_MULTIPLY:
            return binary_operation_multiply;
        default:
            return NULL;
    }
}

/* Recommended canonical pattern catalogue - 8. Opaque handles and release. */
CTD_TEST_API ctd_counter *ctd_counter_create(int initial_value) {
    ctd_counter *counter;

    counter = (ctd_counter *)malloc(sizeof(*counter));

    if (counter == NULL) {
        return NULL;
    }

    counter->value = initial_value;
    return counter;
}

CTD_TEST_API ctd_status ctd_counter_get(const ctd_counter *counter, int *result) {
    if (counter == NULL || result == NULL) {
        return CTD_ERROR_NULL;
    }

    *result = counter->value;
    return CTD_OK;
}

CTD_TEST_API ctd_status ctd_counter_add(ctd_counter *counter, int amount, int *result) {
    if (counter == NULL || result == NULL) {
        return CTD_ERROR_NULL;
    }

    if ((amount > 0 && counter->value > INT_MAX - amount) ||
        (amount < 0 && counter->value < INT_MIN - amount)) {
        return CTD_ERROR_RANGE;
    }

    counter->value += amount;
    *result = counter->value;

    return CTD_OK;
}

CTD_TEST_API ctd_accumulator *ctd_accumulator_create(size_t capacity) {
    ctd_accumulator *accumulator;

    if (capacity > SIZE_MAX / sizeof(int32_t)) {
        return NULL;
    }
    accumulator = (ctd_accumulator *)malloc(sizeof(*accumulator));
    if (accumulator == NULL) {
        return NULL;
    }
    accumulator->values = capacity == 0
        ? NULL
        : (int32_t *)malloc(capacity * sizeof(*accumulator->values));
    if (capacity != 0 && accumulator->values == NULL) {
        ctd_free(accumulator);
        return NULL;
    }
    accumulator->count = 0;
    accumulator->capacity = capacity;
    accumulator->total = 0;
    return accumulator;
}

CTD_TEST_API ctd_status ctd_accumulator_add(
    ctd_accumulator *accumulator,
    int32_t value
) {
    if (accumulator == NULL) {
        return CTD_ERROR_NULL;
    }
    if (accumulator->count == accumulator->capacity) {
        return CTD_ERROR_CAPACITY;
    }
    if ((value > 0 && accumulator->total > INT64_MAX - value) ||
        (value < 0 && accumulator->total < INT64_MIN - value)) {
        return CTD_ERROR_RANGE;
    }
    accumulator->values[accumulator->count] = value;
    accumulator->count += 1;
    accumulator->total += value;
    return CTD_OK;
}

CTD_TEST_API ctd_status ctd_accumulator_get(
    const ctd_accumulator *accumulator,
    int64_t *result
) {
    if (accumulator == NULL || result == NULL) {
        return CTD_ERROR_NULL;
    }
    *result = accumulator->total;
    return CTD_OK;
}

CTD_TEST_API void ctd_accumulator_destroy(ctd_accumulator *accumulator) {
    if (accumulator == NULL) {
        return;
    }
    ctd_free(accumulator->values);
    ctd_free(accumulator);
}

CTD_TEST_API void ctd_free(void *pointer) {
    free(pointer);
}
