---
url: https://chatgpt.com/c/6a786079-f408-83eb-87b1-e0d35b2804a5
---

# SQLite C Extension Template

A working template for developing a C SQLite extension, integrating it directly into a customized SQLite amalgamation, and testing both its **SQLite-facing behavior** and its **underlying C implementation** with Pytest.

The repository uses a small `alphabet` extension as the primary worked example. The extension is deliberately simple enough that the surrounding project structure, build integration, API design, and testing strategy remain visible.

The project combines three concerns that are often treated separately:

1. **SQLite extension development** in ordinary C.
2. **Integration into an extended SQLite build** rather than relying only on runtime loadable extensions.
3. **Direct testing of C implementation APIs from Python** using CFFI and Pytest.

The result is intended as a reusable starting point for small or medium SQLite extensions whose implementation contains C logic worth testing independently of the SQL interface.

---

## Project Goals

The central goal is to provide a practical project pattern for a SQLite extension that can be:

* developed as normal C source;
* integrated directly into SQLite;
* included in a generated SQLite amalgamation;
* automatically initialized as part of the resulting SQLite build;
* exercised through its public SQL interface;
* exposed selectively in test builds for direct C-level testing;
* called from Python through a generated CFFI API-mode wrapper;
* tested comprehensively using ordinary Pytest tests.

The project deliberately avoids treating the SQL interface as the only testable surface.

For nontrivial extensions, substantial logic may live below the `sqlite3_create_function()`, virtual-table, collation, or other SQLite registration layer. Testing all of that logic indirectly through SQL can make tests unnecessarily coarse and can obscure defects at the C API boundary.

This template therefore uses two complementary testing layers:

```text
                    Pytest
                      |
          +-----------+-----------+
          |                       |
          v                       v
      sqlite3                  CFFI API
          |                       |
          v                       v
    SQLite SQL API         direct C test API
          |                       |
          +-----------+-----------+
                      |
                  alphabet.c
```

SQL tests verify the extension as SQLite sees it.

CFFI tests verify selected implementation routines directly.

---

## Worked Extension: `alphabet`

The repository's primary example extension is `alphabet`.

It provides the SQLite function:

```sql
alpha_string(language [, start [, length]])
```

The function returns part or all of a predefined alphabet.

Supported language identifiers include English/Latin and Russian/Cyrillic names.

Examples:

```sql
SELECT alpha_string('en');
SELECT alpha_string('English', 3);
SELECT alpha_string('ru', -5);
SELECT alpha_string('Russian', 2, 4);
```

The extension demonstrates several concerns that are useful beyond the specific example:

* SQLite scalar-function registration;
* UTF-8 text handling in C;
* Unicode code-point indexing;
* optional SQL arguments;
* negative indexing;
* argument validation;
* SQLite error reporting;
* static extension data;
* helper routines that are useful to test independently of SQLite.

The implementation includes lower-level routines such as UTF-8 byte counting, code-point length calculation, byte-offset calculation, and alphabet selection. These provide a useful boundary between **SQLite adapter code** and **independently testable C logic**.

---

## Design Principle: Keep the C Logic Testable

A SQLite extension normally contains at least two conceptual layers:

```text
SQLite interface layer
    |
    | sqlite3_value_*
    | sqlite3_result_*
    | sqlite3_create_function()
    | extension initialization
    |
    v
implementation logic
```

The SQLite interface layer necessarily depends on SQLite's runtime API.

The underlying implementation often does not.

This project keeps useful implementation routines sufficiently separated so they can be tested directly.

The objective is **not** to redesign production code around Python or CFFI. The objective is to expose selected existing C interfaces in a controlled test build.

Production and test linkage can therefore differ without changing the implementation itself.

Conceptually:

```c
#ifdef ALPHABET_TEST
## define AB_TEST_API /* exported test interface */
#else
## define AB_TEST_API static
#endif
```

A helper can remain internal in an ordinary build while becoming externally visible in a test build.

This avoids permanently expanding the production API merely for testability.

---

## Source/API Split

The example extension uses a small header architecture designed to serve both the C compiler and CFFI.

Conceptually:

```text
alphabet.c
    implementation

alphabet.h
    C-facing wrapper header
    linkage/visibility definitions
    ordinary C includes

alphabet_api.h
    declaration catalogue
    CFFI-compatible API declarations
```

`alphabet_api.h` acts as the declaration catalogue for the interfaces that may be tested directly.

The same declarations are ultimately consumed by:

```text
C compiler
    ^
    |
alphabet.h
    |
alphabet_api.h
    |
    v
CFFI cdef preparation
```

This avoids maintaining an unrelated handwritten Python-side copy of every prototype.

The declaration catalogue is intentionally constrained to syntax that can be transformed safely into CFFI `cdef()` input.

It is not intended to become a general-purpose C parser or binding-description language.

---

## Why CFFI

The project uses **CFFI API mode** for direct C testing.

CFFI provides a useful middle ground between:

* manually implementing a Python extension;
* manually reproducing every C ABI detail with `ctypes`;
* introducing a large general-purpose binding generator.

The test wrapper is compiled against the real C declarations.

Conceptually:

```text
alphabet_api.h
       |
       | transformed declarations
       v
   FFI.cdef()
       |
       | generated wrapper
       v
_alphabet_wrapper
       |
       | linked against test SQLite
       v
   sqlite3.dll
       |
       v
 exported alphabet test API
```

Python tests then import the generated wrapper:

```python
from _alphabet_wrapper import ffi, lib
```

and call C functions through `lib`.

This keeps Pytest as the test runner while allowing tests to exercise native C interfaces directly.

---

## Test-Build Exposure

Direct C testing requires selected implementation symbols to be externally visible.

The template therefore distinguishes between:

* **production linkage**, where implementation helpers may remain `static`;
* **test linkage**, where selected routines are exported from the test SQLite library.

For `alphabet`, this is controlled by test-build macros such as:

```text
ALPHABET_TEST
ALPHABET_BUILD_LIB
```

The same pattern is demonstrated more extensively by the CTD reference module included in the project.

The principle is:

> Test visibility is a build property, not a requirement that implementation helpers become permanent public production APIs.

Functions that exist in production can simply change linkage in the test build.

Interfaces that exist only for testing may additionally be enclosed in test-only conditional compilation.

---

## Extended SQLite Build

The extension is not tested only as a separately loaded DLL.

The project builds a customized SQLite distribution and integrates additional C sources into SQLite's source-generation workflow.

At a high level:

```text
SQLite source tree
      +
project extension sources
      +
selected SQLite ext/misc sources
      |
      v
source preparation
      |
      v
EXTRA_SRC
      |
      v
SQLite Makefile.msc
      |
      v
generated / extended amalgamation
      |
      v
sqlite3.dll
libsqlite3.lib
sqlite3.lib
sqlite3.exe
```

The project uses SQLite's existing amalgamation/build hooks rather than maintaining local patches to core SQLite build files.

Important mechanisms include:

```text
EXTRA_SRC
SQLITE_EXTRA_AUTOEXT
```

Selected ordinary extensions are prepared for built-in integration and automatic registration.

The `alphabet` extension follows the same general integration pipeline.

### Detailed build-system documentation

The complete Windows/MSVC build design, including:

* SQLite source acquisition;
* ZLIB and ICU integration;
* FP16 staging;
* `EXTRA_SRC`;
* `SQLITE_EXTRA_AUTOEXT`;
* stock `ext/misc` preparation;
* amalgamation generation;
* export generation;
* static and import libraries;
* x86/x64 handling;
* caching and incremental builds;

is documented separately in:

**[Field Notes — SQLite MSVC Build / Amalgamation Integration](https://github.com/pchemguy/Field-Notes/tree/main/11-sqlite-msvc-build)**

That document should be treated as the detailed build-system reference. This README concentrates on how the build system supports the extension-development and testing workflow.

---

## Why Integrate the Extension into SQLite?

SQLite extensions are commonly developed as independent loadable libraries. That model remains useful, but direct integration provides a different set of properties.

For this template, integration allows the project to exercise:

* built-in extension registration;
* amalgamation generation with project sources;
* test-only symbol exposure from the resulting SQLite library;
* direct linkage of CFFI wrappers against the same native library used by SQLite;
* a build that can be deployed without separately loading the extension at runtime.

It also makes the test build an accurate representation of an **embedded extension** rather than merely a dynamically loaded plugin.

The project does not imply that amalgamation integration is preferable for every SQLite extension. It demonstrates the pattern for projects where embedding is desirable.

---

## Two Complementary Testing Surfaces

### 1. SQL-Level Tests

The SQL-facing API is tested using Python's `sqlite3` module and Pytest.

These tests treat the extension as a SQLite feature and verify behavior such as:

* extension availability;
* accepted language names;
* full alphabet generation;
* start offsets;
* negative offsets;
* requested lengths;
* UTF-8 results;
* boundary conditions;
* invalid language identifiers;
* invalid argument types;
* invalid ranges;
* SQLite error behavior.

These are integration tests across:

```text
Python sqlite3
    ->
SQLite
    ->
extension registration
    ->
alphabet SQL adapter
    ->
implementation
```

They answer the question:

> Does the extension behave correctly through SQLite?

---

### 2. Direct C API Tests

A second Pytest layer imports `_alphabet_wrapper` and tests selected C routines directly through CFFI.

Typical targets include:

```c
int ab_utf8_byte_count(const char *zText);
int64_t ab_utf8_length(const char *zText);
int ab_utf8_byte_offset(const char *zText, int64_t i);
const char *ab_alphabet_select(const char *zLanguage);
```

These tests can verify implementation behavior without passing through:

```text
sqlite3_value
sqlite3_context
SQL parsing
SQLite type conversion
SQLite result handling
```

They answer a different question:

> Does the underlying C implementation obey its own API contract?

Both layers are required for comprehensive testing.

A passing C test does not prove correct SQLite integration.

A passing SQL test does not necessarily isolate defects in the underlying C routines.

---

## CFFI Testing Model

The direct-testing strategy follows the broader design developed in:

**[CFFI Pytest C Testing](https://github.com/pchemguy/CFFI_Pytest_C_Testing)**

That project explores systematic testing of C APIs through CFFI, including:

* scalar values;
* enums and constants;
* global data;
* scalar pointers;
* arrays;
* byte buffers;
* strings;
* structures;
* callbacks;
* owned and borrowed memory;
* opaque handles;
* failure contracts;
* capacity/query protocols;
* test-only linkage.

This SQLite extension template applies that design to a real embedded-library context rather than attempting to reproduce the entire reference catalogue.

The `alphabet` API needs only a small subset of those patterns, but follows the same general rules.

---

## C/Python Boundary Contract

Direct CFFI tests should be derived from the **actual C API contract**, not from superficial prototype shapes.

For every tested API, determine:

* parameter and return types;
* valid input ranges;
* NULL rules;
* pointer direction;
* pointer shape;
* string encoding;
* length/count units;
* ownership;
* lifetime;
* mutations and side effects;
* failure behavior.

A pointer declaration alone is insufficient.

For example:

```c
const char *zText
```

does not by itself tell a test author whether the pointer is:

* nullable;
* NUL-terminated;
* UTF-8;
* borrowed;
* retained;
* copied;
* valid only for the duration of the call.

Those properties are part of the API contract.

The direct test suite should establish them from declarations, comments, and implementation before constructing test cases.

---

## Memory and Ownership Policy

The practical testing model is intentionally conservative.

### Python-owned memory

Memory created using:

```python
ffi.new(...)
```

belongs to Python/CFFI.

It must not be passed to a C deallocator.

The owning CData object must remain alive while C accesses it.

### Python buffers

Memory exposed with:

```python
ffi.from_buffer(...)
```

remains owned by the Python object providing the buffer.

### Borrowed C memory

Pointers returned to static or otherwise library-owned storage are borrowed.

Python tests must not free them.

Where independent Python lifetime is useful, tests should copy the contents.

For strings:

```python
ffi.string(ptr)
```

For arrays:

```python
ffi.unpack(ptr, count)
```

### C-owned allocations

If a future extension API returns allocated memory, the corresponding ownership and release routine must be part of the explicit API contract.

Python and C allocators must never be mixed.

---

## Pytest as the Test Runner

There is no custom native test runner.

Pytest remains responsible for:

* fixture lifecycle;
* test discovery;
* parameterization;
* assertions;
* failure reporting;
* CFFI wrapper setup;
* SQL connection setup.

The native library is simply another implementation surface consumed by the tests.

This is an important project constraint:

```text
Pytest
  is the test runner.

CFFI
  provides the C boundary.

SQLite
  provides the SQL boundary.
```

---

## Test Organization

A practical suite should keep SQL-facing and direct-C tests visibly separate.

Conceptually:

```text
tests/
├─ conftest.py
│
├─ test_alphabet_sql.py
│
├─ test_alphabet_utf8.py
├─ test_alphabet_selection.py
└─ ...
```

The exact decomposition can evolve with the extension, but tests should be grouped according to the interface contract they verify rather than placed in one monolithic module.

---

## Test Design Rules

Tests should be derived from the implementation contract.

For every target:

1. inspect its declaration;
2. inspect its implementation;
3. determine its valid domain;
4. determine its boundary conditions;
5. determine its failure behavior;
6. determine ownership and mutation semantics where relevant;
7. only then design test cases.

Do not infer behavior merely from a function name.

Do not copy a superficially similar test pattern without checking whether the target has the same pointer, lifetime, size, or failure contract.

Parameterized tests should use descriptive IDs that communicate the behavioral case being exercised.

For example:

```python
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(b"", 0, id="empty"),
        pytest.param(b"A", 1, id="ascii-single"),
        pytest.param("Я".encode(), 2, id="utf8-two-byte"),
    ],
)
```

is preferable to anonymous parameter sets whose meaning is visible only from the raw values.

---

## `alphabet` as a Template, Not a Framework

The repository is intentionally not a generic extension generator or binding framework.

`alphabet` is a concrete implementation used to establish repeatable project patterns.

A new extension can replace or extend it while retaining the same broad architecture:

```text
src/
    myextension.c
    myextension.h
    myextension_api.h

build integration
    ->
extended SQLite

test build macros
    ->
selected C symbols exported

CFFI builder
    ->
_myextension_wrapper

tests/
    ->
SQL tests
    +
direct C tests
```

The project favors a small number of explicit conventions over machinery intended to handle arbitrary C APIs automatically.

---

## Intended Scope

The testing architecture is aimed primarily at deterministic, synchronous C code such as:

* algorithms;
* parsers;
* encoding/decoding routines;
* data transformations;
* numeric routines;
* string handling;
* structured data manipulation;
* SQLite extension implementation logic.

It is not intended to provide universal automation for every possible C interface.

In particular, specialized system programming, hardware interfaces, unusual process control, arbitrary asynchronous callbacks, platform-specific kernel facilities, and highly dynamic ownership protocols may require project-specific testing approaches.

The objective is broad practical coverage, not pretend generality.

---

## Build Layout

Generated and downloaded build state is kept under:

```text
out/
```

The build system currently distinguishes normal and test build trees:

```text
out/
├─ cache/
├─ sqlite/
├─ build/
├─ build_test/
├─ bin/
├─ include/
└─ lib/
   ├─ import/
   └─ static/
```

Important outputs include:

```text
out\bin\sqlite3.dll
out\bin\sqlite3.exe

out\include\sqlite3.h
out\include\sqlite3ext.h
out\include\alphabet.h
out\include\alphabet_api.h

out\lib\import\sqlite3.def
out\lib\import\sqlite3.lib

out\lib\static\libsqlite3.lib
```

A test build uses `out\build_test` and enables the extension's test API exposure.

See the dedicated build Field Note for the complete directory and build-stage description.

---

## Windows/MSVC Build

The primary native build is Windows/MSVC.

Run the build from an initialized Visual C++ developer command prompt matching the required architecture.

Typical invocation:

```cmd
build_sqlite_msvc.bat
```

The build configuration is controlled by environment switches including:

```text
USE_TEST
USE_ICU
USE_ZLIB
USE_FP16
SQLITE_EXTRA
USE_EXTRAS
```

For the CFFI-focused test build, the important properties are:

```text
USE_TEST=1
USE_EXTRAS=1
```

with project-specific test symbols exported into the resulting SQLite DLL.

The currently recommended SQLite test configuration also disables integrations that conflict with SQLite's own test build:

```cmd
set USE_TEST=1
set USE_ICU=0
set SQLITE_EXTRA=0
set USE_EXTRAS=1

build_sqlite_msvc.bat
```

The precise build machinery is intentionally not duplicated here. See:

**[SQLite MSVC build Field Note](https://github.com/pchemguy/Field-Notes/tree/main/11-sqlite-msvc-build)**

---

## Typical Development Workflow

A practical extension-development cycle is:

#### 1. Implement or modify the extension

Work primarily under:

```text
src/
```

Keep SQLite-facing adapter code and reusable implementation logic reasonably distinguishable.

#### 2. Define the test-visible C contract

Add or maintain the relevant declarations in the extension API catalogue.

Use test linkage macros for implementation routines that should remain internal in production.

#### 3. Build the extended SQLite test library

Build SQLite with project extras and test API exposure enabled.

#### 4. Build the CFFI wrapper

Generate/compile `_alphabet_wrapper` against the produced native library and the same declaration catalogue used by the C compiler.

#### 5. Run Pytest

Run both:

* SQL-level tests;
* direct CFFI tests.

#### 6. Diagnose at the appropriate boundary

A failure in a direct C test generally points toward the C implementation or its API contract.

A failure that occurs only through SQL generally points toward the SQLite adapter, registration, argument conversion, or result/error handling.

This separation is one of the principal benefits of the architecture.

---

## Project Structure

The important source-level components are conceptually:

```text
.
├─ README.md
├─ pyproject.toml
├─ build_sqlite_msvc.bat
│
├─ src/
│  ├─ alphabet.c
│  ├─ alphabet.h
│  ├─ alphabet_api.h
│  │
│  ├─ ctd.c
│  ├─ ctd.h
│  └─ ctd_api.h
│
├─ tool/
│  ├─ patch_sqlite_misc_autoext.tcl
│  └─ bundle_extra_src.tcl
│
├─ tests/
│  ├─ conftest.py
│  └─ test_*.py
│
└─ out/
   └─ generated build state
```

`ctd` is a broader C interface fixture/reference used to develop and validate CFFI testing patterns.

`alphabet` is the actual SQLite extension template demonstrating application of those patterns.

---

## Relationship to the Reference Projects

This repository sits at the intersection of two related pieces of work.

### SQLite build/integration reference

[**Field Notes — SQLite MSVC Build**](https://github.com/pchemguy/Field-Notes/tree/main/11-sqlite-msvc-build)

Covers the build side in depth:

* integrating ordinary extensions into the amalgamation;
* `EXTRA_SRC`;
* `SQLITE_EXTRA_AUTOEXT`;
* automatic extension registration;
* source patching;
* dependency bundling;
* Windows/MSVC build mechanics.

### CFFI/Pytest reference

[**CFFI Pytest C Testing**](https://github.com/pchemguy/CFFI_Pytest_C_Testing)

Covers the C/Python testing boundary in depth:

* CFFI API mode;
* test-only symbol exposure;
* linkage modes;
* C declaration catalogues;
* scalar/pointer/array/buffer/string interfaces;
* structures and callbacks;
* ownership and lifetime;
* direct Pytest testing patterns.

This project combines those two ideas in the context of an actual SQLite extension.

---

## What This Repository Demonstrates

The useful result is not the alphabet function itself.

The repository demonstrates a complete path:

```text
C extension implementation
        |
        v
test-aware C declaration/API design
        |
        v
SQLite EXTRA_SRC integration
        |
        v
extended SQLite amalgamation
        |
        v
MSVC test DLL with selected exported internals
        |
        +-----------------------+
        |                       |
        v                       v
SQLite SQL API            CFFI API wrapper
        |                       |
        +-----------+-----------+
                    |
                    v
                  Pytest
```

That path makes it possible to develop an embedded SQLite extension while retaining ordinary, focused unit tests for the C implementation underneath it.

---

## Status

This repository should be regarded as a **development template and reference implementation**, not as a general C binding framework or an official SQLite build mechanism.

Its conventions are deliberately optimized for:

* small C extensions;
* explicit APIs;
* deterministic behavior;
* maintainable Pytest suites;
* direct visibility into the Python/C boundary;
* minimal permanent intrusion into production linkage;
* reproducible extension-development structure.

The project is expected to evolve as additional C interface patterns and SQLite extension designs are exercised.
