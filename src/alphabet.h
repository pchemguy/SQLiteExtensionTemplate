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
**   AB_BUILD_STATIC_LIB
**       Build a static library with ordinary external linkage.
**
**   AB_TEST + AB_BUILD_LIB
**       Build the test shared library and export AB symbols.
**
**   AB_TEST + AB_USE_LIB
**       Consume the test shared library and import AB symbols.
*/

#if defined(AB_BUILD_LIB) && defined(AB_USE_LIB)
#  error "AB_BUILD_LIB and AB_USE_LIB are mutually exclusive"
#endif

#if defined(AB_TEST) && defined(AB_BUILD_STATIC_LIB)
#  error "AB_TEST and AB_BUILD_STATIC_LIB are mutually exclusive"
#endif

#if defined(AB_TEST) && \
    !defined(AB_BUILD_LIB) && !defined(AB_USE_LIB)
#  error "AB_TEST requires AB_BUILD_LIB or AB_USE_LIB"
#endif


#if defined(AB_TEST)

#  if defined(AB_BUILD_LIB)

#    if defined(_WIN32)
#      define AB_TEST_API             __declspec(dllexport)
#      define AB_TEST_DATA_API extern __declspec(dllexport)
#    elif defined(__GNUC__) || defined(__clang__)
#      define AB_TEST_API             __attribute__((visibility("default")))
#      define AB_TEST_DATA_API extern __attribute__((visibility("default")))
#    else
#      define AB_TEST_API
#      define AB_TEST_DATA_API extern
#    endif

#    define AB_TEST_DATA_DEF

#  elif defined(AB_USE_LIB)

#    if defined(_WIN32)
#      define AB_TEST_API             __declspec(dllimport)
#      define AB_TEST_DATA_API extern __declspec(dllimport)
#    else
#      define AB_TEST_API
#      define AB_TEST_DATA_API extern
#    endif

/*
** A library consumer must not compile AB data definitions. Define this
** macro only to make accidental use produce an immediate compiler error.
*/
#    define AB_TEST_DATA_DEF AB_TEST_DATA_DEF_IS_NOT_ALLOWED_IN_A_LIBRARY_CONSUMER

#  endif

#elif defined(AB_BUILD_STATIC_LIB)

#  define AB_TEST_API
#  define AB_TEST_DATA_API extern
#  define AB_TEST_DATA_DEF

#else

#  define AB_TEST_API      static
#  define AB_TEST_DATA_API static
#  define AB_TEST_DATA_DEF static

#endif /* AB_TEST */


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
