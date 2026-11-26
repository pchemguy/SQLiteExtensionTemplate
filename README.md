---
projects:
  - https://chatgpt.com/g/g-p-6a660e31e55c8191805f7e5893694e70
  - https://chatgpt.com/g/g-p-6a60b416edf081918615b69ac96e4304
urls:
  - https://chatgpt.com/c/6a786079-f408-83eb-87b1-e0d35b2804a5
  - https://chatgpt.com/c/6b06bdd1-be88-83ea-b551-049981ea67cd
---

# SQLite C Extension Template

This template integrates **Alphabet**, a minimal demo extension written in C, into the SQLite core and tests both its SQL interface and its C API from Python. **CTD**, a C module with no SQLite dependency, illustrates the broader aim: testing a component through its own C API while it remains part of a larger library.

## Overview

The Windows build harness compiles both components into the SQLite amalgamation (`sqlite3.c`). They expose different interfaces:

- [**Alphabet**](src/alphabet.c) provides the scalar SQL function `alpha_string()` and a [C API](src/alphabet_api.h) for UTF-8 traversal and alphabet selection. In the SQL-enabled build, Alphabet is a built-in auto-extension: its initializer registers `alpha_string()` on each new connection without loading a separate extension DLL. Python’s `sqlite3` exercises SQL registration, argument handling, results and errors; a compiled CFFI API-mode wrapper calls the helpers exported by the test build.
- [**CTD**](src/ctd_api.h) is a standalone C module from [CFFI_Pytest_C_Testing](https://github.com/pchemguy/CFFI_Pytest_C_Testing). It implements only a C API: it calls no SQLite routines and has no SQL functions or SQLite initializer. Its examples demonstrate how to test pointers, buffers, structures, callbacks, ownership and failure behavior from Python with CFFI and pytest.

The template is intended for small or medium SQLite extensions with C logic worth testing independently of SQL. It supplies the Alphabet and CTD build hooks and one C API test preset. The primary source for the Windows build harness is [SQLite-ICU-MinGW’s Current/MSVC README](https://github.com/pchemguy/SQLite-ICU-MinGW/blob/master/Current/MSVC/README.md).

> [!IMPORTANT]
>
> **AI-Assisted Development Disclosure**
>
> This project has been developed with extensive generative-AI assistance. Assistance covered project exploration, design discussion, specification development, implementation, testing, technical review, and documentation. See [AI_DISCLOSURE.md](AI_DISCLOSURE.md) for further details. Responsibility for the published software remains with the maintainer.

The [SQLite MSVC build field note](https://github.com/pchemguy/Field-Notes/tree/main/notes/11-sqlite-msvc-build) explains how the harness integrates loadable extensions into the amalgamation and registers them automatically on each new connection.

## Build the worked example on Windows

Run the commands from the repository root in Windows CMD. Install the Visual C++ Build Tools with a Windows SDK and use a checkout path without spaces for the project hooks.

**Use one base directory per build.** Keep each architecture, build configuration or dependency installation in a separate checkout or copy of the template. The harness stages dependencies under `out\sqlite` and packages headers and libraries outside `out\build`. The CFFI builder also writes the wrapper and copies binaries under `alphabet\src\alphabet`. Replacing only `out\build` does not isolate two configurations.

### Prepare the Python environment

If you already have a dedicated test environment with architecture-matched Python, CFFI, setuptools and pytest, use it with the matching MSVC toolchain and skip the bundled setup. The bundled Python environment targets x64.

> [!CAUTION]
> The bundled scripts also change the Windows user profile. The [environment launcher](pyenv/conda_far.bat) removes existing `%LOCALAPPDATA%\pip\cache` and `%LOCALAPPDATA%\uv\cache` directories and replaces them with junctions to its selected caches. On first bootstrap, [Anaconda.bat](pyenv/Anaconda.bat) also removes `%APPDATA%\mamba` if it exists. To leave those locations untouched, use your own environment and skip both commands below.

To use the bundled environment, start a clean `cmd.exe /d /e:on /v:on` with `CONDA_PREFIX` unset and with `python.exe` and `conda.bat` absent from `PATH`. Create the environment on first use, then activate it in the current prompt:

```cmd
call pyenv\Anaconda.bat
call pyenv\conda_far.bat /batch
```

The bootstrap creates `pyenv\Anaconda` and reuses it when its `python.exe` exists. The launcher calls its sibling `pyenv\msbuild.bat` **before** Conda activation and sets `DISTUTILS_USE_SDK=1` after successful MSVC verification. Set SQLite build switches after activation.

### Choose a test build

Choose **one** of the two configurations below for this checkout. Both export the Alphabet and CTD C APIs; only the full-suite configuration registers `alpha_string()`.

**Building local changes.** The project hooks fetch missing C sources and headers from this repository’s `main` branch, then reuse the files in `out\cache\SQLiteExtensionTemplate\src`. For local edits or a checkout at a different revision, seed the cache from that checkout before compiling. When rebuilding edited sources within the **same configuration**, start with a fresh `out\build` so NMAKE regenerates the amalgamation. [Commands for local source edits](sqlite_msbuild.md#building-local-source-edits)

#### Full suite: SQL and C API tests

Call the main harness directly with the [full-suite settings](sqlite_msbuild.md#build-for-the-full-test-suite). `SQLITE_EXTRA=1` includes the auto-extension dispatcher and enables ZLIB. This recipe does not require ICU.

```cmd
set "USE_ICU=0"
set "SQLITE_EXTRA=1"
set "USE_EXTRAS=1"
set "SQLITE_ENABLE_ALPHABET=1"
set "USE_TEST=1"
cmd /d /c sqlite_msbuild.bat
```

`USE_EXTRAS=1` runs both project hooks, but only Alphabet has a SQL feature to enable:

- The [Alphabet hook](sqlite_ext_alphabet.bat) skips the component when `SQLITE_ENABLE_ALPHABET=0`. Otherwise it adds `-DSQLITE_ENABLE_ALPHABET`, the compile definition that guards the dispatcher’s call to `sqlite3AlphabetInit(db)`.
- There is no `SQLITE_ENABLE_CTD` switch. The [CTD hook](sqlite_ext_ctd.bat) adds `ctd.c` whenever project hooks run. CTD has no SQLite initializer for the dispatcher to call.

`USE_TEST=1` enables the C exports of the included components; it does not register SQL functions. To check SQL registration in this build, run the following query in its shell. It returns `ABC`:

```cmd
out\bin\sqlite3.exe ":memory:" "SELECT alpha_string('en', 0, 3);"
```

#### C API tests only: template preset

Run the [single preset](sqlite_msbuild_extra.bat) in a child CMD to keep its settings local. It enables the project hooks and C test exports with ICU, ZLIB and the stock stage disabled.

```cmd
cmd /d /c sqlite_msbuild_extra.bat
```

With this preset, `no such function: alpha_string` is expected. Select the DLL used by Python and compile the wrapper as described below, but skip the SQL registration checks.

## Test with Python

### Select the SQLite DLL used by pytest

The fixtures import Python’s `sqlite3` module before loading the CFFI wrapper. Copying a DLL beside the wrapper does not replace the one Python has already loaded. Run the [DLL path helper](tool/sqlite3_dll_path.py) with the interpreter you will use for pytest:

```cmd
python tool\sqlite3_dll_path.py
```

Use the path the helper reports. If it finds no separately loaded `sqlite3.dll`, this replacement method does not apply. In a dedicated test environment, close processes using the DLL and back up the original. When the reported path is `%CONDA_PREFIX%\Library\bin\sqlite3.dll`, replace it with the architecture-matched build:

```cmd
copy /y "out\bin\sqlite3.dll" "%CONDA_PREFIX%\Library\bin\sqlite3.dll"
```

A fresh Python process in that environment loads the replacement when it imports `sqlite3`. For either test configuration above, **copy only `sqlite3.dll`**. The preset disables ZLIB; the full-suite build links it statically by default, so the `zlib1.dll` collected in `out\bin` is not required by `sqlite3.dll`. Both recipes disable ICU. If you deliberately enable ICU and use the same Conda environment that supplied it for the build, its matching ICU DLLs are already in `%CONDA_PREFIX%\Library\bin`.

### Check SQL registration (full-suite build only)

Start a fresh Python process after replacing the DLL. Before compiling the wrapper, check that Python’s `sqlite3` can call `alpha_string()` and that SQLite registered all three arities:

```cmd
python -c "import sqlite3; db=sqlite3.connect(':memory:'); print(db.execute('SELECT alpha_string(?, ?, ?)', ('en', 0, 3)).fetchone()[0])"
python -m pytest alphabet\tests\test_registration.py
```

The first command prints `ABC`. The registration test checks for arities 1, 2 and 3.

### Compile the CFFI wrapper and run pytest

Use the same Python and an active MSVC environment. The SQLite harness collects `sqlite3*.h` under `out\include`. The wrapper compiler also needs the original `alphabet.h`, `ctd.h` and their `_api.h` catalogues. Copy the project's headers from the same revision used for the DLL before invoking the builder.

```cmd
copy /y "src\*.h" "out\include\"
python alphabet\src\alphabet\build_wrapper.py
```

The builder discovers each `src\*_api.h` with its matching `.c` and `.h`. In CFFI’s out-of-line API mode, the builder reads the catalogue for `ffi.cdef()` and the C compiler checks the generated wrapper against the staged component headers. The builder compiles a single **`_cffi_wrapper`** with `<NAME>_TEST` and `<NAME>_USE_LIB` and links it against the import libraries in `out\lib\import`; the C implementation stays in `sqlite3.dll`. It writes the wrapper under `alphabet\src\alphabet` and copies the contents of `out\bin` beside it. The pytest fixtures import that prebuilt module and expose its `ffi` and `lib` objects. [Wrapper builder](alphabet/src/alphabet/build_wrapper.py) · [Fixtures](alphabet/tests/conftest.py)

With the template’s preset, run the C API tests for both modules.

```cmd
python -m pytest ^
  alphabet\tests\test_alphabet_helpers.py ^
  alphabet\tests\test_alphabet_wrapper_api.py ^
  alphabet\tests\test_cffi_usage_patterns.py ^
  alphabet\tests\test_globals_status_and_scalars.py ^
  alphabet\tests\test_pointers_arrays_and_bytes.py ^
  alphabet\tests\test_strings_structures_and_ownership.py
```

With the SQL-enabled test build, run the entire suite.

```cmd
python -m pytest alphabet\tests
```

### What each test proves

| Test surface | Examples in this repository |
| --- | --- |
| Alphabet SQL registration and behavior | Arity and flags, argument validation, Unicode slicing, NULL propagation, expression indexes, and execution with an untrusted schema. [Registration](alphabet/tests/test_registration.py) · [SQL contract](alphabet/tests/test_alpha_string_sql.py) · [SQL contexts](alphabet/tests/test_sql_context.py) |
| Alphabet C API | Function signatures, byte widths, code-point counts, byte offsets, and lifetime of borrowed alphabet strings. [Helper tests](alphabet/tests/test_alphabet_helpers.py) · [Wrapper API tests](alphabet/tests/test_alphabet_wrapper_api.py) |
| CTD C API | Mutable globals, failure contracts, pointer and buffer capacities, callbacks, structured data and C-owned allocations. [Pointers and buffers](alphabet/tests/test_pointers_arrays_and_bytes.py) · [Ownership](alphabet/tests/test_strings_structures_and_ownership.py) · [CFFI usage](alphabet/tests/test_cffi_usage_patterns.py) |

A passing C helper test does not show that SQLite registered the SQL function. If the helpers pass but Python reports `no such function: alpha_string`, check [which configuration you built](#choose-a-test-build) and [which DLL Python loaded](#select-the-sqlite-dll-used-by-pytest). Conversely, an expected SQL result does not prove that the DLL exports the C symbols or that a helper honors its buffer and lifetime contracts. Those are direct C API checks.

### Testing CTD inside a larger library

In the [standalone CTD build](https://github.com/pchemguy/CFFI_Pytest_C_Testing#standalone-ctd-build), the CFFI wrapper links against `ctd.dll`, which contains only CTD. Here the wrapper links against the test build of `sqlite3.dll`, which contains CTD alongside Alphabet and SQLite itself. No separate CTD DLL is needed.

The [original callback test](https://github.com/pchemguy/CFFI_Pytest_C_Testing/blob/main/ctd/tests/test_cffi_usage_patterns.py) and [its counterpart in this template](alphabet/tests/test_cffi_usage_patterns.py) illustrate what stays the same: both pass a Python callback and user data to `lib.ctd_apply_callback()` and check that it returns `CTD_OK` and writes `32` to the output. The test exercises the component through its own C API regardless of which DLL contains it.

## The Alphabet SQL interface

```sql
alpha_string(language [, start [, length]])
```

`'en'` and `'English'` select the 52-character Latin alphabet. `'ru'` and `'Russian'` select the 66-character Russian alphabet including Ё and ё. Names are case-insensitive, and each alphabet lists uppercase letters before lowercase letters. `start` is a zero-based Unicode code-point index. Negative indices count from the end, and a start at the end returns an empty string. `length` is a nonnegative integer capped at the number of remaining code points. A NULL in any supplied argument returns NULL. Invalid types, unknown languages and out-of-range indices raise SQL errors.

```sql
SELECT alpha_string('English', 0, 3);  -- ABC
SELECT alpha_string('Russian', 2, 4);  -- ВГДЕ
SELECT alpha_string('ru', -2);         -- юя
```

### Built-in and loadable extension registration

The SQLite-facing code lives in one internal registration routine. The three fixed arities let SQLite reject an unsupported argument count before calling `alphabetStringFunc()`. The first registration error is returned to the caller. [Source](src/alphabet.c)

```c
/*
** Register the extension's SQL functions.
**
** Three fixed arities are registered so SQLite itself rejects calls with
** zero arguments or more than three arguments.
*/
static int alphabetInit(sqlite3 *db) {
    static const int flags = SQLITE_UTF8 | SQLITE_DETERMINISTIC | SQLITE_INNOCUOUS;
    int rc = SQLITE_OK;

    if (rc == SQLITE_OK) {
        rc = sqlite3_create_function(
            db, "alpha_string", 1, flags, 0,
            alphabetStringFunc, 0, 0
        );
    }

    if (rc == SQLITE_OK) {
        rc = sqlite3_create_function(
            db, "alpha_string", 2, flags, 0,
            alphabetStringFunc, 0, 0
        );
    }

    if (rc == SQLITE_OK) {
        rc = sqlite3_create_function(
            db, "alpha_string", 3, flags, 0,
            alphabetStringFunc, 0, 0
        );
    }

    return rc;
}
```

The two entry points in the same source file share that routine. In the integrated build with stock extensions enabled, the dispatcher calls `sqlite3AlphabetInit(db)` when SQLite opens a database connection. A standalone loadable build exports `sqlite3_alphabet_init`, which first initializes the SQLite API dispatch table from `pApi`. The Windows harness builds the integrated form.

```c
#ifdef SQLITE_CORE

int sqlite3AlphabetInit(sqlite3 *db) {
    return alphabetInit(db);
}

#else

# if defined(_WIN32)
__declspec(dllexport)
# endif
int sqlite3_alphabet_init(
    sqlite3 *db,
    char **pzErrMsg,
    const sqlite3_api_routines *pApi
) {
    SQLITE_EXTENSION_INIT2(pApi);
    (void)pzErrMsg;  /* Unused parameter */
    return alphabetInit(db);
}

#endif /* SQLITE_CORE */
```

## The test-visible C contract

The implementation, linkage rules and declaration catalogue have separate jobs. For Alphabet, `alphabet.c` implements the SQL adapter and four helper routines, `alphabet.h` selects linkage and includes the catalogue, and `alphabet_api.h` declares the helpers and documents their preconditions. CTD uses the same file arrangement. [Alphabet header](src/alphabet.h) · [Alphabet API catalogue](src/alphabet_api.h) · [CTD header](src/ctd.h)

In a production build `ALPHABET_TEST_API` gives the helpers internal linkage. In the test DLL, `ALPHABET_TEST` with `ALPHABET_BUILD_LIB` exports them. The wrapper consumes the same declarations with `ALPHABET_TEST` and `ALPHABET_USE_LIB`. CTD uses the corresponding `CTD_*` macros. This makes selected routines testable directly while the SQL interface stays the same.

The API catalogue records details the C types alone cannot express. For example, `ab_utf8_length()` expects valid, NUL-terminated UTF-8. `ab_utf8_byte_offset()` takes a code-point index in the documented range and returns a byte offset. `ab_alphabet_select()` returns borrowed static storage for a supported language or a null pointer for an unknown name. Direct tests exercise those contracts, and the SQL tests exercise validation before SQLite passes values to the helpers.

One direct test passes the pointer returned by one C function straight to another. The expected length is measured in code points even when the Russian string occupies two bytes per letter. [Alphabet wrapper tests](alphabet/tests/test_alphabet_wrapper_api.py)

```python
@pytest.mark.parametrize(
    ("language", "expected_length"),
    [
        pytest.param(b"en", 52, id="selected-latin"),
        pytest.param(b"ru", 66, id="selected-cyrillic"),
    ],
)
def test_utf8_length_accepts_borrowed_alphabet_storage(
    ffi: Any, lib: Any, language: bytes, expected_length: int
) -> None:
    alphabet = lib.ab_alphabet_select(language)
    assert alphabet != ffi.NULL
    assert lib.ab_utf8_length(alphabet) == expected_length
```

Keep borrowed storage alive while C uses it. For each CTD allocation, use the release function documented for that return value:

| Value | What the caller must do |
| --- | --- |
| Storage passed with `ffi.new()` or `ffi.from_buffer()` | Keep the owning Python/CFFI object alive while C uses it. Do not pass it to a C deallocator. |
| Borrowed string from `ab_alphabet_select()` | Do not free it. Use `ffi.string()` to make an independent Python copy when needed. |
| Counter from `ctd_counter_create()` or sequence from `ctd_alloc_sequence_i32()` | Release each successful allocation once with `ctd_free()`. |
| Handle from `ctd_accumulator_create()` | Use `ctd_accumulator_destroy()`. It releases the nested storage as well as the handle; `ctd_free()` alone does not. |

The [CTD API catalogue](src/ctd_api.h) documents these contracts. The [fixtures](alphabet/tests/conftest.py) demonstrate resetting mutable globals and pairing allocations with release; the [accumulator lifecycle test](alphabet/tests/test_strings_structures_and_ownership.py) shows the type-specific destructor in a `finally` block.

## Adapting the template

1. **Define the C contract.** For each component the wrapper should expose, provide `src\<name>.c`, `src\<name>.h` and `src\<name>_api.h`. The [wrapper builder](alphabet/src/alphabet/build_wrapper.py) scans every `*_api.h` and checks that the matching linkage header contains `<NAME>_TEST` and defines `<NAME>_TEST_API`. Keep compiler-only includes and linkage logic in `<name>.h`. The catalogue supplies the declarations for `ffi.cdef()`; document pointer direction, valid ranges, length units, ownership, lifetime and failure behavior there.
2. **Stage your own sources.** Add a `sqlite_ext_<name>.bat` hook beside `sqlite_msbuild.bat`; `USE_EXTRAS=1` runs the project hooks. When copying the [Alphabet hook](sqlite_ext_alphabet.bat), change `URL_PREFIX`, the filenames and the cache path to use your own repository and intended revision. Stage the sources and headers in `tsrc`, run the patcher and bundler on the staged C file, and append it to `EXTRA_SRC`. When `USE_TEST=1`, add `-D<NAME>_TEST` and `-D<NAME>_BUILD_LIB` to `OPT_XTRA`.
3. **Register SQL features separately from compiling them.** For a SQL extension, provide an initializer the [patcher](tool/patch_sqlite_misc_autoext.tcl) recognizes, such as `sqlite3AlphabetInit`. Enable the matching dispatcher guard (for Alphabet, `SQLITE_ENABLE_ALPHABET`) in the hook and build with `SQLITE_EXTRA=1` to include the dispatcher. Adding a C file to `EXTRA_SRC` alone does not register a SQL function. A plain C module like [CTD](sqlite_ext_ctd.bat) needs neither a SQLite initializer nor a dispatcher guard.
4. **Verify the result.** Rebuild SQLite, check the [DLL exports](sqlite_msbuild.md#exports-and-packaged-files) and, for a SQL extension, check registration on a new connection. Stage the matching headers, compile the wrapper, then test the C contract and the SQL behavior through their respective interfaces.

## Repository guide

| Path | Contents |
| --- | --- |
| [sqlite_msbuild.bat](sqlite_msbuild.bat) and [sqlite_msbuild.md](sqlite_msbuild.md) | Native build entry point, template preset, feature switches, cache and rebuild instructions. |
| [msbuild.bat](msbuild.bat) and [pyenv/](pyenv/) | MSVC discovery and verification, plus the Python bootstrap and activation scripts. |
| [src/](src/) and [tool/](tool/) | Project C sources and declaration catalogues, Tcl preparation scripts and development utilities. |
| [alphabet/src/alphabet/](alphabet/src/alphabet/) | CFFI builder, CTD demonstration, wrapper introspection and SQLite metadata utilities. |
| [alphabet/tests/](alphabet/tests/) and [pyproject.toml](pyproject.toml) | pytest suite and Python project configuration. |
| `out\` (generated) | `cache` holds downloaded inputs, `sqlite` the extracted tree, and `build` the NMAKE working files. Packaged outputs go to `bin`, `include`, `lib\import` and `lib\static`. |

## Further examples

| Extension | What it demonstrates |
| --- | --- |
| [SQLiteICUex](https://github.com/pchemguy/SQLiteICUex) | Registers the ICU-backed `UTF_CI` and `UTF_CI_AI` collations and exposes Unicode case folding and normalization through `str_casefold()` and `str_normalize()`. |
| [SQLitePackedBlob](https://github.com/pchemguy/SQLitePackedBlob) | `pblob_pack()` encodes a one-dimensional JSON array of numbers as a binary16 or binary32 BLOB; `pblob_unpack()` decodes it to JSON text. |
| [SQLiteRegexpMatches](https://github.com/pchemguy/SQLiteRegexpMatches) | Reuses SQLite’s `ext/misc/regexp.c` in the amalgamation. `regexp_matches()` and `regexpi_matches()` return non-overlapping matches as a JSON array. |

## Summary

- Keep SQL registration and argument handling in the SQLite adapter. The same registration routine can serve both built-in and loadable entry points.
- Use a project hook to stage the C implementation and a shared `*_api.h` catalogue to declare the routines worth testing directly. Test-build macros expose those routines from `sqlite3.dll` without making them public in the normal build.
- Test the same DLL through both interfaces: Python’s `sqlite3` for Alphabet’s SQL registration and behavior, and the compiled CFFI wrapper for Alphabet’s helpers and CTD’s C API. CTD can be tested inside SQLite without adding a SQL adapter.
