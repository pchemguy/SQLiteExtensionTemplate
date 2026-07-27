# SQLite Alphabet Extension Template

A compact SQLite C extension project that demonstrates how to:

- implement a scalar SQL function in C;
- build SQLite with the extension integrated into the target `sqlite3.dll`;
- register the extension for both core and standalone builds;
- test the SQL-visible contract through Python's `sqlite3` module and `pytest`;
- keep generated SQLite sources and build outputs outside the tracked source tree.

The extension currently provides one SQL function:

```sql
alpha_string(language [, start [, length]])
```

It returns the English Latin or Russian Cyrillic alphabet, optionally sliced by Unicode code-point index.

---

## 1. Project Status

The current implementation phase focuses on:

1. the extension source in `src/alphabet.c`;
2. the existing SQLite/MSVC build workflow;
3. SQL-level behavioral testing through `pytest`.

Direct C unit tests for private helper functions are intentionally outside the current scope. The initial test system treats the SQL interface as the public contract and verifies it through the same SQLite library used by Python.

---

## 2. Repository Layout

```text
TOP/
├── README.md
├── pyproject.toml
├── sqlite_MSVC_Cpp_Build_Tools.ext.bat
│
├── src/
│   └── alphabet.c
│
├── tool/
│   └── *.tcl
│
└── pytestenv/
    ├── src/
    │   └── pytestenv/
    │       └── sqlite_dbmeta.py
    │
    └── tests/
        ├── conftest.py
        ├── support.py
        ├── test_environment.py
        ├── test_registration.py
        ├── test_language.py
        ├── test_start.py
        ├── test_length.py
        ├── test_null.py
        ├── test_types.py
        └── test_sql_context.py
```

The exact set of test modules may evolve, but tests remain under:

```text
TOP/pytestenv/tests
```

The Python package under `pytestenv/src/pytestenv` exists to support the pytest project layout. The extension itself is implemented in C and is not a Python extension module.

The module `pytestenv/src/pytestenv/sqlite_dbmeta.py` is used to query metadata for the SQLite library copy used by Python.

---

## 3. Extension Interface

### 3.1 Function signature

```sql
alpha_string(language [, start [, length]])
```

Supported arities:

```sql
alpha_string(language)
alpha_string(language, start)
alpha_string(language, start, length)
```

Calls with zero arguments or more than three arguments are rejected by SQLite because the extension registers three fixed arities.

### 3.2 Language selector

The mandatory `language` argument must be SQL `TEXT`.

Accepted values are matched case-insensitively:

| Language | Accepted selectors |
|---|---|
| English Latin | `en`, `English` |
| Russian Cyrillic | `ru`, `Russian` |

Examples:

```sql
SELECT alpha_string('en');
SELECT alpha_string('English');
SELECT alpha_string('RU');
SELECT alpha_string('russian');
```

Unsupported selector strings produce an SQL error.

Values with a non-text SQLite storage class also produce an SQL error. The function does not silently convert integers, real values, or blobs to text.

### 3.3 Start index

The optional `start` argument must be SQL `INTEGER`.

The current interface uses a zero-based Unicode code-point index:

```sql
SELECT alpha_string('en', 0);
```

returns the complete English alphabet.

A negative `start` counts backward from the end:

```sql
SELECT alpha_string('en', -1);
```

returns:

```text
z
```

Valid range:

```text
-length(alphabet) <= start <= length(alphabet)
```

The endpoint equal to the alphabet length is valid and returns an empty string.

Values outside the valid range produce an SQL error.

### 3.4 Length

The optional `length` argument must be SQL `INTEGER` and must not be negative.

It specifies the maximum number of Unicode code points returned from the normalized start position.

Examples:

```sql
SELECT alpha_string('en', 0, 3);
-- ABC

SELECT alpha_string('en', -5, 2);
-- vw

SELECT alpha_string('ru', 0, 4);
-- АБВГ
```

If `length` exceeds the remaining number of code points, the result is truncated at the end of the alphabet.

A zero length returns an empty string.

### 3.5 NULL behavior

`NULL` propagates from every supplied argument.

Examples:

```sql
SELECT alpha_string(NULL);
SELECT alpha_string('en', NULL);
SELECT alpha_string('en', 0, NULL);
```

Each expression returns SQL `NULL`.

---

## 4. Alphabet Data

The extension embeds two UTF-8 string literals.

English Latin:

```text
ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz
```

Russian Cyrillic:

```text
АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя
```

The implementation slices strings by Unicode code points rather than UTF-8 bytes.

Consequently:

- Latin code points occupy one UTF-8 byte each;
- Cyrillic code points in the current alphabet occupy two UTF-8 bytes each;
- indexing remains defined in code points, not storage bytes.

---

## 5. C Extension Architecture

The implementation is contained in:

```text
src/alphabet.c
```

No public extension header is required.

The source supports two compilation modes.

### 5.1 SQLite core or amalgamation build

When `SQLITE_CORE` is defined, the source includes:

```c
#include "sqlite3.h"
```

and exposes the internal initializer:

```c
int sqlite3AlphabetInit(sqlite3 *db);
```

This form is intended for integration into the SQLite build.

### 5.2 Standalone loadable-extension build

When `SQLITE_CORE` is not defined, the source includes:

```c
#include "sqlite3ext.h"
SQLITE_EXTENSION_INIT1
```

and exports:

```c
int sqlite3_alphabet_init(
  sqlite3 *db,
  char **pzErrMsg,
  const sqlite3_api_routines *pApi
);
```

The standalone initializer calls the shared registration function.

### 5.3 SQL function properties

`alpha_string()` is registered with:

```c
SQLITE_UTF8
SQLITE_DETERMINISTIC
SQLITE_INNOCUOUS
```

These flags establish that:

- the function accepts UTF-8 text;
- identical inputs produce identical results;
- the function has no side effects and is safe for restricted schema contexts.

The test suite verifies behavior that depends on these properties, including use in deterministic schema expressions where supported by the target SQLite build.

---

## 6. SQLite Build System

The repository includes an existing Windows/MSVC SQLite build workflow:

```text
sqlite_MSVC_Cpp_Build_Tools.ext.bat
tool/*.tcl
```

The batch file is the build entry point. The Tcl utilities support source preparation and SQLite integration.

The extension source is integrated into the target SQLite build so that the produced `sqlite3.dll` exposes `alpha_string()` without requiring a runtime `load_extension()` call.

### 6.1 Build prerequisites

The build environment requires:

- Windows;
- Microsoft Visual C++ Build Tools or Visual Studio with the C/C++ toolchain;
- `nmake`;
- Tcl compatible with the SQLite build workflow;
- a SQLite source checkpoint expected by the build scripts.

The exact accepted command-line options and directory preparation rules are defined by:

```text
sqlite_MSVC_Cpp_Build_Tools.ext.bat
```

Use the batch file's built-in help or source documentation as the authoritative build interface.

### 6.2 Build output

The target artifact used by the Python tests is:

```text
sqlite3.dll
```

It must be built for the same architecture as the Python interpreter that will run pytest.

For example:

- 64-bit Python requires a 64-bit `sqlite3.dll`;
- debug/release CRT and toolchain choices must remain compatible with the consuming Python runtime;
- the DLL must export the symbols expected by Python's `_sqlite3.pyd`.

---

## 7. Python and Pytest Environment

The repository contains an otherwise minimal Python project used solely as the SQL test harness.

Configuration is stored in:

```text
TOP/pyproject.toml
```

Tests are discovered under:

```text
TOP/pytestenv/tests
```

The test runner is pytest itself:

```cmd
pytest -vv
```

or:

```cmd
python -m pytest -vv
```

There is no custom test runner.

### 7.1 Target SQLite library

The tests use Python's standard `sqlite3` module.

On Windows, Python normally reaches SQLite through:

```text
sqlite3.py
  -> _sqlite3.pyd
    -> sqlite3.dll
```

Before pytest starts, replace the `sqlite3.dll` used by the selected Python installation with the target DLL produced by this project.

This replacement is intentionally outside the pytest suite. The tests do not:

- build SQLite;
- copy DLLs;
- discover build artifacts;
- load a standalone extension;
- start a subordinate test process.

Pytest only verifies the SQL behavior of the SQLite library already loaded by the Python process.

### 7.2 DLL replacement precautions

Observe the following rules:

1. Replace the DLL before starting Python.
2. Ensure no Python process is currently using the DLL.
3. Preserve the original Python DLL if the installation is not disposable.
4. Use a target DLL with the same processor architecture as Python.
5. Start a fresh Python process after replacement.
6. Verify the loaded SQLite build before trusting functional test results.

A dedicated test Python installation is safer than modifying a primary development installation.

A virtual environment may still use the base interpreter's binary modules and DLL directory. Do not assume that creating a virtual environment automatically isolates `sqlite3.dll`.

---

## 8. Test Architecture

The first test implementation is exclusively SQL-facing.

It treats `alpha_string()` as a black-box SQLite scalar function and verifies:

- function registration;
- supported arities;
- accepted inputs;
- exact results;
- Unicode indexing;
- error propagation;
- SQLite storage-class validation;
- NULL propagation;
- deterministic and innocuous registration behavior;
- execution in ordinary SQL contexts.

Private C helper functions are not called directly.

This is intentional: the initial test suite validates the public contract rather than internal implementation details.

---

## 9. Shared Pytest Fixtures

Shared test data and fixtures belong in:

```text
pytestenv/tests/conftest.py
```

Typical shared values include:

- a fresh in-memory SQLite connection;
- a scalar-query helper;
- an SQL-error assertion helper.

Example structure:

```python
from collections.abc import Callable, Iterator
import sqlite3
from typing import Any

import pytest


@pytest.fixture
def connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(":memory:")
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def scalar(
    connection: sqlite3.Connection,
) -> Callable[[str, tuple[Any, ...]], Any]:
    def execute(
        sql: str,
        parameters: tuple[Any, ...] = (),
    ) -> Any:
        row = connection.execute(sql, parameters).fetchone()
        assert row is not None
        return row[0]

    return execute
```

Tests should normally receive fixtures through pytest dependency injection.

Do not import `conftest.py` as an ordinary application module.

A separate `support.py` module provides

- the expected Latin alphabet;
- the expected Cyrillic alphabet;
- extension-defined error messages;

```python
LATIN = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
)

CYRILLIC = (
    "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
)
...
```

---

## 10. Test Modules and Coverage

### 10.1 Environment tests

`test_environment.py` verifies that:

- Python's `sqlite3` module can open a connection;
- SQLite reports a valid version and source ID;
- `alpha_string()` is available;
- the expected arities are present in `pragma_function_list`;
- the loaded SQLite build is the intended target where an exact identity check is configured.

These tests should fail early when Python has loaded the wrong `sqlite3.dll`.

### 10.2 Registration tests

`test_registration.py` verifies:

- one-argument registration;
- two-argument registration;
- three-argument registration;
- rejection of zero arguments;
- rejection of four or more arguments;
- registration metadata exposed by SQLite.

### 10.3 Language tests

`test_language.py` verifies:

- `en`;
- `English`;
- `ru`;
- `Russian`;
- lowercase, uppercase, and mixed-case variants;
- exact complete alphabet values;
- unsupported selector strings;
- leading or trailing whitespace;
- empty selector strings;
- non-text SQLite storage classes.

Representative unsupported selectors include:

```text
""
"eng"
"rus"
"de"
" English"
"English "
"русский"
```

### 10.4 Start-index tests

`test_start.py` verifies:

- omitted start;
- start `0`;
- ordinary positive positions;
- the final code point;
- start equal to alphabet length;
- negative positions;
- negative full length;
- one position above the positive range;
- one position below the negative range;
- minimum and maximum signed 64-bit values;
- non-integer storage classes.

Boundary coverage is more important than testing arbitrary large sets of integer values.

### 10.5 Length tests

`test_length.py` verifies:

- zero length;
- one-code-point length;
- ordinary lengths;
- exact remaining length;
- lengths larger than the remaining suffix;
- negative starts combined with length;
- negative length rejection;
- non-integer storage classes;
- maximum signed 64-bit positive length.

### 10.6 NULL tests

`test_null.py` verifies SQL `NULL` propagation for:

- language;
- start;
- length;
- each supported arity containing a supplied `NULL`.

Tests must distinguish SQL `NULL` from the empty string.

### 10.7 Type tests

`test_types.py` verifies the SQLite storage-class contract.

Typical Python-to-SQLite mappings used by the tests are:

| Python value | SQLite storage class |
|---|---|
| `None` | `NULL` |
| `int` | `INTEGER` |
| `float` | `REAL` |
| `str` | `TEXT` |
| `bytes` | `BLOB` |

The extension deliberately rejects implicit conversions for typed arguments.

For example:

- `"1"` is text, not an accepted integer start;
- `1.0` is real, not an accepted integer start;
- `b"en"` is a blob, not an accepted language selector.

### 10.8 SQL-context tests

`test_sql_context.py` verifies behavior in broader SQL use:

- execution across multiple rows;
- statement failure when one row contains invalid input;
- use inside expressions;
- use in expression indexes;
- use in generated columns or restricted schema contexts;
- interaction with `PRAGMA trusted_schema`.

---

## 11. Error Contract

Extension-generated validation failures are returned with `sqlite3_result_error()` and appear in Python as `sqlite3.OperationalError`.

Current error messages include:

```text
alpha_string() language must be text
alpha_string() language must be en, English, ru, or Russian
alpha_string() start must be an integer
alpha_string() start index is out of range
alpha_string() length must be an integer
alpha_string() length must not be negative
```

Tests should compare extension-defined error messages exactly.

For SQLite-generated errors, such as invalid function arity, tests may match only the stable portion of the message unless the project intentionally pins exact wording to one SQLite checkpoint.

Example:

```python
with pytest.raises(sqlite3.OperationalError) as error:
    connection.execute(
        "SELECT alpha_string('invalid')"
    ).fetchall()

assert str(error.value) == (
    "alpha_string() language must be "
    "en, English, ru, or Russian"
)
```

---

## 12. Running Tests

From `TOP`:

```cmd
python -m pytest -vv
```

To run one module:

```cmd
python -m pytest pytestenv\tests\test_language.py
```

To run one test:

```cmd
python -m pytest ^
  pytestenv\tests\test_language.py::test_english_selectors
```

To select tests by expression:

```cmd
python -m pytest -k start
```

To stop after the first failure:

```cmd
python -m pytest -x
```

To show local variables in tracebacks:

```cmd
python -m pytest -l
```

The canonical project command remains:

```cmd
pytest
```

provided the intended Python environment is active.

---

## 13. Test Isolation

Each test should use a fresh in-memory database:

```python
sqlite3.connect(":memory:")
```

This prevents:

- schema objects leaking between tests;
- pragma state leaking between tests;
- transaction state leaking between tests;
- one failing test affecting later tests.

Function registration belongs to the SQLite connection created by Python's underlying library initialization and is expected to be available on every fresh connection.

Tests that modify connection-level settings, such as `trusted_schema`, must not reuse a connection shared with unrelated tests.

---

## 14. Independent Expected Results

Expected alphabet values must be written independently in the test suite.

Tests must not:

- parse `src/alphabet.c`;
- extract the C macros;
- call `alpha_string()` to generate expected values;
- derive expected aliases or error messages from implementation source.

Duplication between the C constants and test expectations is intentional. It allows tests to detect missing, duplicated, reordered, or accidentally changed letters.

Python string slicing may be used to calculate expected substring results because Python slices Unicode strings by code point, matching the extension's documented indexing unit for the current alphabets.

---

## 15. Development Workflow

A normal development cycle is:

1. edit `src/alphabet.c`;
2. rebuild the target SQLite library with `sqlite_MSVC_Cpp_Build_Tools.ext.bat`;
3. replace the `sqlite3.dll` used by the selected Python test installation;
4. start a fresh Python process;
5. run `pytest`;
6. inspect failures;
7. repeat.

Before accepting a build, verify that:

- Python loaded the intended SQLite checkpoint;
- `alpha_string()` is registered with arities 1, 2, and 3;
- all pytest modules pass;
- the target DLL architecture matches Python;
- no tests were skipped unexpectedly.

---

## 16. Current Scope Exclusions

The first test implementation does not include:

- direct C unit tests for `utf8_byte_count()`;
- direct C unit tests for `utf8_length()`;
- direct C unit tests for `utf8_byte_offset()`;
- direct C unit tests for `alphabet_select()`;
- fuzz testing;
- malformed UTF-8 injection into private helpers;
- SQLite's Tcl `testfixture`;
- a custom test executable;
- a custom test runner;
- automatic DLL deployment from pytest;
- cross-platform builds.

These may be added later if they provide value beyond the SQL contract suite.

---

## 17. Coding Conventions

The extension follows SQLite-oriented C conventions:

- one source module;
- `sqlite3_int64` for SQL integer values;
- explicit SQLite storage-class validation;
- immediate return after setting an error result;
- UTF-8 traversal by code point;
- fixed-arity function registration;
- no public extension API beyond SQLite registration;
- no dynamic allocation for the fixed alphabet data.

Tests should follow corresponding Python conventions:

- pytest fixtures for shared resources;
- parameterization for equivalence classes;
- exact assertions for extension-defined behavior;
- fresh database connection per test;
- bound SQL parameters rather than string interpolation;
- descriptive test names;
- no hidden build or deployment behavior.

---

## 18. Summary

This repository is a focused template for developing an SQLite C extension as part of a customized SQLite/MSVC build.

Its current architecture is intentionally simple:

```text
C extension source
    -> customized sqlite3.dll
        -> Python sqlite3
            -> pytest SQL contract tests
```

The build system owns SQLite compilation and extension integration.

The Python project owns SQL-level verification.

Pytest is the only test runner.
