/*
** ctd.h
**
** Standalone C99 library fixture for exploring Python CFFI.
*/

#ifndef CTD_H
#define CTD_H

#include <stddef.h>
#include <stdint.h>


/****************************** API Declaration ******************************/

/*
** Build modes:
**
**   no defines
**       Production build. CTD symbols have internal linkage.
**
**   CTD_BUILD_STATIC_LIB
**       Build a static library with ordinary external linkage.
**
**   CTD_TEST + CTD_BUILD_LIB
**       Build the test shared library and export CTD symbols.
**
**   CTD_TEST + CTD_USE_LIB
**       Consume the test shared library and import CTD symbols.
*/

#if defined(CTD_BUILD_LIB) && defined(CTD_USE_LIB)
#  error "CTD_BUILD_LIB and CTD_USE_LIB are mutually exclusive"
#endif

#if defined(CTD_TEST) && defined(CTD_BUILD_STATIC_LIB)
#  error "CTD_TEST and CTD_BUILD_STATIC_LIB are mutually exclusive"
#endif

#if defined(CTD_TEST) && \
    !defined(CTD_BUILD_LIB) && !defined(CTD_USE_LIB)
#  error "CTD_TEST requires CTD_BUILD_LIB or CTD_USE_LIB"
#endif


#if defined(CTD_TEST)

#  if defined(CTD_BUILD_LIB)

#    if defined(_WIN32)
#      define CTD_TEST_API             __declspec(dllexport)
#      define CTD_TEST_DATA_API extern __declspec(dllexport)
#    elif defined(__GNUC__) || defined(__clang__)
#      define CTD_TEST_API             __attribute__((visibility("default")))
#      define CTD_TEST_DATA_API extern __attribute__((visibility("default")))
#    else
#      define CTD_TEST_API
#      define CTD_TEST_DATA_API extern
#    endif

#    define CTD_TEST_DATA_DEF

#  elif defined(CTD_USE_LIB)

#    if defined(_WIN32)
#      define CTD_TEST_API             __declspec(dllimport)
#      define CTD_TEST_DATA_API extern __declspec(dllimport)
#    else
#      define CTD_TEST_API
#      define CTD_TEST_DATA_API extern
#    endif

/*
** A library consumer must not compile CTD data definitions. Define this
** macro only to make accidental use produce an immediate compiler error.
*/
#    define CTD_TEST_DATA_DEF CTD_TEST_DATA_DEF_IS_NOT_ALLOWED_IN_A_LIBRARY_CONSUMER

#  endif

#elif defined(CTD_BUILD_STATIC_LIB)

#  define CTD_TEST_API
#  define CTD_TEST_DATA_API extern
#  define CTD_TEST_DATA_DEF

#else

#  define CTD_TEST_API      static
#  define CTD_TEST_DATA_API static
#  define CTD_TEST_DATA_DEF static

#endif /* CTD_TEST */


#ifdef __cplusplus
extern "C" {
#endif

/*
** Constants.
*/
#define CTD_LATIN \
  "ABCDEFGHIJKLMNOPQRSTUVWXYZ" \
  "abcdefghijklmnopqrstuvwxyz"


/*
** Canonical API pattern catalogue:
**
**   1. Globals, constants, enums, and status values.
**   2. Scalar value operations.
**   3. Scalar pointer operations.
**   4. Typed arrays.
**   5. Capacity-bounded byte buffers.
**   6. NUL-terminated strings.
**   7. Structures and tagged unions.
**   8. Opaque handles, ownership, and release.
**
** Each applicable family includes success, boundary, NULL, failure, and
** capacity-reporting protocols.
*/


#include "ctd_api.h"

#ifdef __cplusplus
}
#endif

#endif /* CTD_H */
