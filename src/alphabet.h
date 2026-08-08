/*
** alphabet.h
**
*/

#ifndef ALPHABET_H
#define ALPHABET_H

#include <stdint.h>

#ifndef SQLITE_CORE
# include "sqlite3ext.h"
  SQLITE_EXTENSION_INIT1
#else
# include "sqlite3.h"
#endif

/****************************** API Declaration ******************************/

/*
** Build modes:
**
**   no defines
**       Production build. AB symbols have internal linkage.
**
**   ALPHABET_BUILD_STATIC_LIB
**       Build a static library with ordinary external linkage.
**
**   ALPHABET_TEST + ALPHABET_BUILD_LIB
**       Build the test shared library and export AB symbols.
**
**   ALPHABET_TEST + ALPHABET_USE_LIB
**       Consume the test shared library and import AB symbols.
*/

#if defined(ALPHABET_BUILD_LIB) && defined(ALPHABET_USE_LIB)
#  error "ALPHABET_BUILD_LIB and ALPHABET_USE_LIB are mutually exclusive"
#endif

#if defined(ALPHABET_TEST) && defined(ALPHABET_BUILD_STATIC_LIB)
#  error "ALPHABET_TEST and ALPHABET_BUILD_STATIC_LIB are mutually exclusive"
#endif

#if defined(ALPHABET_TEST) && \
    !defined(ALPHABET_BUILD_LIB) && !defined(ALPHABET_USE_LIB)
#  error "ALPHABET_TEST requires ALPHABET_BUILD_LIB or ALPHABET_USE_LIB"
#endif


#if defined(ALPHABET_TEST)

#  if defined(ALPHABET_BUILD_LIB)

#    if defined(_WIN32)
#      define ALPHABET_TEST_API             __declspec(dllexport)
#      define ALPHABET_TEST_DATA_API extern __declspec(dllexport)
#    elif defined(__GNUC__) || defined(__clang__)
#      define ALPHABET_TEST_API             __attribute__((visibility("default")))
#      define ALPHABET_TEST_DATA_API extern __attribute__((visibility("default")))
#    else
#      define ALPHABET_TEST_API
#      define ALPHABET_TEST_DATA_API extern
#    endif

#    define ALPHABET_TEST_DATA_DEF

#  elif defined(ALPHABET_USE_LIB)

#    if defined(_WIN32)
#      define ALPHABET_TEST_API             __declspec(dllimport)
#      define ALPHABET_TEST_DATA_API extern __declspec(dllimport)
#    else
#      define ALPHABET_TEST_API
#      define ALPHABET_TEST_DATA_API extern
#    endif

/*
** A library consumer must not compile AB data definitions. Define this
** macro only to make accidental use produce an immediate compiler error.
*/
#    define ALPHABET_TEST_DATA_DEF ALPHABET_TEST_DATA_DEF_IS_NOT_ALLOWED_IN_A_LIBRARY_CONSUMER

#  endif

#elif defined(ALPHABET_BUILD_STATIC_LIB)

#  define ALPHABET_TEST_API
#  define ALPHABET_TEST_DATA_API extern
#  define ALPHABET_TEST_DATA_DEF

#else

#  define ALPHABET_TEST_API      static
#  define ALPHABET_TEST_DATA_API static
#  define ALPHABET_TEST_DATA_DEF static

#endif /* ALPHABET_TEST */


#define LATIN_UTF8 \
  "ABCDEFGHIJKLMNOPQRSTUVWXYZ" \
  "abcdefghijklmnopqrstuvwxyz"

#define CYRILLIC_UTF8 \
  "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ" \
  "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"


#ifdef __cplusplus
extern "C" {
#endif

#include "alphabet_api.h"

#ifdef __cplusplus
}
#endif

#endif /* ALPHABET_H */
