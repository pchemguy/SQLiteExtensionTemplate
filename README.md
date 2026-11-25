---
projects:
  - https://chatgpt.com/g/g-p-6a660e31e55c8191805f7e5893694e70
  - https://chatgpt.com/g/g-p-6a60b416edf081918615b69ac96e4304
urls:
  - https://chatgpt.com/c/6a786079-f408-83eb-87b1-e0d35b2804a5
  - https://chatgpt.com/c/6b06bdd1-be88-83ea-b551-049981ea67cd
---

# SQLite C Extension Template

A working template for developing a C SQLite extension, integrating it directly into a customized SQLite amalgamation, and testing both its **SQLite-facing behavior** and its **underlying C implementation** with pytest.

The worked extension, **alphabet**, implements the `alpha_string()` SQL function. Python's `sqlite3` module exercises that interface when the build registers alphabet on each connection. A compiled CFFI wrapper lets pytest call the underlying UTF-8 and alphabet-selection routines directly. A second C module, **CTD**, supplies examples of testing pointers, buffers, callbacks and ownership. [Alphabet implementation](src/alphabet.c) · [CTD interface](src/ctd_api.h)

The template is intended for small or medium SQLite extensions whose implementation contains C logic worth testing independently of the SQL interface. It supplies the alphabet and CTD build hooks and a single test preset. The primary source for the Windows build harness is [SQLite-ICU-MinGW’s Current/MSVC README](https://github.com/pchemguy/SQLite-ICU-MinGW/blob/master/Current/MSVC/README.md).

> [!IMPORTANT]
>
> **AI-Assisted Development Disclosure**
>
> This project has been developed with extensive generative-AI assistance. Assistance covered project exploration, design discussion, specification development, implementation, testing, technical review, and documentation. See [AI_DISCLOSURE.md](AI_DISCLOSURE.md) for further details. Responsibility for the published software remains with the maintainer.

## Build the worked example on Windows

Run the commands below from the repository root. Use a checkout path without spaces for the project hooks. Install the Visual C++ Build Tools with a Windows SDK. The bundled Python environment targets x64. If your active environment already has architecture-matched Python, CFFI, setuptools and pytest, go straight to the build command.

To use the repository's Python environment, start a clean `cmd.exe /d /e:on /v:on` with `CONDA_PREFIX` unset and with `python.exe` and `conda.bat` absent from `PATH`. Create the environment on first use, then activate it in the current prompt.

```cmd
call pyenv\Anaconda.bat
call pyenv\conda_far.bat /batch
```

The bootstrap creates `pyenv\Anaconda` and reuses it when its `python.exe` exists. The launcher calls its sibling `pyenv\msbuild.bat` **before** Conda activation and sets `DISTUTILS_USE_SDK=1` after successful MSVC verification. Set SQLite build switches after activation. [Bootstrap](pyenv/Anaconda.bat) · [Environment launcher](pyenv/conda_far.bat)

**Building local changes.** The project hooks download missing C sources and headers from this repository's `main` branch and then reuse files in `out\cache\SQLiteExtensionTemplate\src`. If you edit `src\` or check out another revision, seed that cache from the checkout and start with a fresh `out\build` before compiling. [Commands for local source edits](sqlite_msbuild.md#building-local-source-edits)

**For the C API tests**, run the template’s preset in a child CMD to keep its settings local. It exports the alphabet and CTD APIs with ICU, zlib and the stock SQLite extensions disabled. [Preset script](sqlite_msbuild_extra.bat)

```cmd
cmd /d /c sqlite_msbuild_extra.bat
```

**For the full SQL and C API suite**, call `sqlite_msbuild.bat` with `SQLITE_EXTRA=1`, `USE_EXTRAS=1` and `USE_TEST=1`. The stock stage registers `alpha_string()` on each new connection. The preset skips that stage. Start with a fresh `out\build` when switching configurations. [Build commands for the full suite](sqlite_msbuild.md#build-for-the-full-test-suite)

Check the SQL-enabled shell from the repository root. The query returns `ABC`.

```cmd
out\bin\sqlite3.exe ":memory:" "SELECT alpha_string('en', 0, 3);"
```

## Test with Python

### Select the SQLite DLL used by pytest

The test fixtures import Python’s `sqlite3` module before loading the CFFI wrapper. To use the same build for both, first locate the SQLite DLL loaded by the test interpreter. [DLL path helper](tool/sqlite3_dll_path.py)

```cmd
python tool\sqlite3_dll_path.py
```

In the dedicated test environment, save the original DLL before replacing it with `out\bin\sqlite3.dll`. For example, the following command applies **when the helper reports `%CONDA_PREFIX%\Library\bin\sqlite3.dll`**. Close any process using that DLL before copying.

```cmd
copy /y "out\bin\sqlite3.dll" "%CONDA_PREFIX%\Library\bin\sqlite3.dll"
```

Use the reported location for other Python distributions. The interpreter needs a separately loaded, architecture-matched `sqlite3.dll` and access to the enabled runtime dependencies. For the SQL-enabled build, the harness collects `zlib1.dll` in `out\bin`. With that build, you can check SQL registration in a fresh Python process before compiling the wrapper.

```cmd
python -c "import sqlite3; db=sqlite3.connect(':memory:'); print(db.execute('SELECT alpha_string(?, ?, ?)', ('en', 0, 3)).fetchone()[0])"
python -m pytest alphabet\tests\test_registration.py
```

Expect `ABC` and registrations for arities 1, 2 and 3.

### Compile the CFFI wrapper and run pytest

Use the same Python and an active MSVC environment. The SQLite harness collects `sqlite3*.h` under `out\include`. The wrapper compiler also needs the original `alphabet.h`, `ctd.h` and their `_api.h` catalogues. Copy the project's headers from the same revision used for the DLL before invoking the builder.

```cmd
copy /y "src\*.h" "out\include\"
python alphabet\src\alphabet\build_wrapper.py
```

The builder discovers each `src\*_api.h` with its matching `.c` and `.h`, prepares the declarations for `ffi.cdef()`, and includes each component header in generated C. It compiles a single **`_cffi_wrapper`** against the import libraries in `out\lib\import` with `<NAME>_TEST` and `<NAME>_USE_LIB`. It writes the extension under `alphabet\src\alphabet` and copies the contents of `out\bin` beside it. The pytest fixtures import that prebuilt module and expose its `ffi` and `lib` objects. [Wrapper builder](alphabet/src/alphabet/build_wrapper.py) · [Fixtures](alphabet/tests/conftest.py)

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

| Test surface | Examples in this repository |
| --- | --- |
| SQL registration and behavior | Arity and flags, argument validation, Unicode slicing, NULL propagation, expression indexes, and execution with an untrusted schema. [Registration](alphabet/tests/test_registration.py) · [SQL contract](alphabet/tests/test_alpha_string_sql.py) · [SQL contexts](alphabet/tests/test_sql_context.py) |
| Alphabet C API | Function signatures, byte widths, code-point counts, byte offsets, and lifetime of borrowed alphabet strings. [Helper tests](alphabet/tests/test_alphabet_helpers.py) · [Wrapper API tests](alphabet/tests/test_alphabet_wrapper_api.py) |
| CTD C API | Mutable globals, failure contracts, pointer and buffer capacities, callbacks, structured data and C-owned allocations. [Pointers and buffers](alphabet/tests/test_pointers_arrays_and_bytes.py) · [Ownership](alphabet/tests/test_strings_structures_and_ownership.py) · [CFFI usage](alphabet/tests/test_cffi_usage_patterns.py) |

## The alphabet SQL interface

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

The implementation, linkage rules and declaration catalogue have separate jobs. For alphabet, `alphabet.c` implements the SQL adapter and four helper routines, `alphabet.h` selects linkage and includes the catalogue, and `alphabet_api.h` declares the helpers and documents their preconditions. CTD uses the same file arrangement. [Alphabet header](src/alphabet.h) · [Alphabet API catalogue](src/alphabet_api.h) · [CTD header](src/ctd.h)

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

For CFFI tests, keep the owner of `ffi.new()` or `ffi.from_buffer()` storage alive while C uses it. Copy a borrowed string into Python with `ffi.string()` when an independent value is needed. Release CTD-owned allocations with `ctd_free()` as specified by that API. The fixtures demonstrate resetting mutable globals and pairing allocation with release. [CTD API catalogue](src/ctd_api.h) · [Fixture examples](alphabet/tests/conftest.py)

## Adapting the template

1. Put the C implementation, linkage header and API catalogue under `src\`. Define the SQL registration and the contracts for the C routines that need direct tests.
2. Add a sibling `sqlite_ext_<name>.bat` hook that stages the intended version of the source and headers. Append its C source to `EXTRA_SRC` and its feature and test-export definitions to `OPT_XTRA`. Alphabet shows SQL registration and CTD shows how to add a plain C module. [Alphabet hook](sqlite_ext_alphabet.bat) · [CTD hook](sqlite_ext_ctd.bat)
3. Rebuild SQLite and check SQL registration and DLL exports. Stage matching headers for the wrapper, rebuild it, and exercise both surfaces with pytest. Document pointer direction, valid ranges, length units, ownership, lifetime and failure behavior when extending the C API. [Build and export checks](sqlite_msbuild.md#exports-and-packaged-files)

## Repository guide

| Path | Contents |
| --- | --- |
| [sqlite_msbuild.bat](sqlite_msbuild.bat) and [sqlite_msbuild.md](sqlite_msbuild.md) | Native build entry point, template preset, feature switches, cache and rebuild instructions. |
| [msbuild.bat](msbuild.bat) and [pyenv/](pyenv/) | MSVC discovery and verification, plus the Python bootstrap and activation scripts. |
| [src/](src/) and [tool/](tool/) | Project C sources and declaration catalogues, Tcl preparation scripts and development utilities. |
| [alphabet/src/alphabet/](alphabet/src/alphabet/) | CFFI builder, CTD demonstration, wrapper introspection and SQLite metadata utilities. |
| [alphabet/tests/](alphabet/tests/) and [pyproject.toml](pyproject.toml) | pytest suite and Python project configuration. |
| `out\` (generated) | `cache` holds downloaded inputs, `sqlite` the extracted tree, and `build` the NMAKE working files. Packaged outputs go to `bin`, `include`, `lib\import` and `lib\static`. |

For background on the two techniques used in the template, see the [SQLite MSVC build field note](https://github.com/pchemguy/Field-Notes/tree/main/notes/11-sqlite-msvc-build) and the [CFFI/pytest C testing reference](https://github.com/pchemguy/CFFI_Pytest_C_Testing).
