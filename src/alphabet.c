/*
** alphabet.c
**
** SQLite extension providing:
**
**   alpa_string(selector [, start [, length]])
**
** selector:
**   "en" or "English"  -> Latin alphabet
**   "ru" or "Russian"  -> Russian Cyrillic alphabet
**
** selector matching is case-insensitive.
**
** start is a zero-based Unicode code-point index. A negative value counts
** backward from the end of the selected alphabet.
**
** length is an optional non-negative number of Unicode code points.
**
** Examples:
**
**   SELECT alpa_string('en');
**   SELECT alpa_string('English', 3);
**   SELECT alpa_string('ru', -5);
**   SELECT alpa_string('Russian', 2, 4);
*/

#ifndef SQLITE_CORE
# include "sqlite3ext.h"
  SQLITE_EXTENSION_INIT1
#else
# include "sqlite3.h"
#endif

#define ALPHABET_LATIN_UTF8 \
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

#define ALPHABET_CYRILLIC_UTF8 \
  "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ" \
  "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"

/*
** Return the byte length of the UTF-8 code point beginning at z.
**
** The function is used only with the fixed, valid UTF-8 strings above.
*/
static int alphabetUtf8CharBytes(const unsigned char *z){
  if( z[0] < 0x80 ) return 1;
  if( (z[0] & 0xE0) == 0xC0 ) return 2;
  if( (z[0] & 0xF0) == 0xE0 ) return 3;
  return 4;
}

/* Return the number of Unicode code points in a valid UTF-8 string. */
static sqlite3_int64 alphabetUtf8Length(const char *z){
  const unsigned char *p = (const unsigned char *)z;
  sqlite3_int64 n = 0;

  while( *p!=0 ){
    p += alphabetUtf8CharBytes(p);
    ++n;
  }
  return n;
}

/*
** Return the byte offset corresponding to Unicode code-point index i.
** The caller guarantees 0 <= i <= alphabetUtf8Length(z).
*/
static int alphabetUtf8ByteOffset(const char *z, sqlite3_int64 i){
  const unsigned char *p = (const unsigned char *)z;
  const unsigned char *pStart = p;

  while( i>0 ){
    p += alphabetUtf8CharBytes(p);
    --i;
  }
  return (int)(p - pStart);
}

/*
** Resolve a selector to one of the supported alphabet strings.
** Return NULL for an unsupported selector.
*/
static const char *alphabetSelect(const char *zSelector){
  if( sqlite3_stricmp(zSelector, "en")==0
   || sqlite3_stricmp(zSelector, "English")==0
  ){
    return ALPHABET_LATIN_UTF8;
  }

  if( sqlite3_stricmp(zSelector, "ru")==0
   || sqlite3_stricmp(zSelector, "Russian")==0
  ){
    return ALPHABET_CYRILLIC_UTF8;
  }

  return 0;
}

/* SQL implementation of alpa_string(). */
static void alphabetStringFunc(
  sqlite3_context *context,
  int argc,
  sqlite3_value **argv
){
  const char *zSelector;
  const char *zAlphabet;
  sqlite3_int64 nChars;
  sqlite3_int64 iStart = 0;
  sqlite3_int64 nResult;
  int iByteStart;
  int iByteEnd;

  /*
  ** NULL propagates. This also permits calls such as
  ** alpa_string('en', NULL) to return NULL.
  */
  if( sqlite3_value_type(argv[0])==SQLITE_NULL
   || (argc>=2 && sqlite3_value_type(argv[1])==SQLITE_NULL)
   || (argc>=3 && sqlite3_value_type(argv[2])==SQLITE_NULL)
  ){
    sqlite3_result_null(context);
    return;
  }

  zSelector = (const char *)sqlite3_value_text(argv[0]);
  if( zSelector==0 ){
    sqlite3_result_error_nomem(context);
    return;
  }

  zAlphabet = alphabetSelect(zSelector);
  if( zAlphabet==0 ){
    sqlite3_result_error(
      context,
      "alpa_string() selector must be en, English, ru, or Russian",
      -1
    );
    return;
  }

  nChars = alphabetUtf8Length(zAlphabet);

  if( argc>=2 ){
    if( sqlite3_value_type(argv[1])!=SQLITE_INTEGER ){
      sqlite3_result_error(
        context,
        "alpa_string() start must be an integer",
        -1
      );
      return;
    }
    iStart = sqlite3_value_int64(argv[1]);

    if( iStart<0 ){
      /*
      ** Avoid signed overflow for extremely negative values.
      ** Any value less than -nChars clamps to the beginning.
      */
      if( iStart < -nChars ){
        iStart = 0;
      }else{
        iStart += nChars;
      }
    }else if( iStart>nChars ){
      iStart = nChars;
    }
  }

  nResult = nChars - iStart;

  if( argc>=3 ){
    sqlite3_int64 nRequested;

    if( sqlite3_value_type(argv[2])!=SQLITE_INTEGER ){
      sqlite3_result_error(
        context,
        "alpa_string() length must be an integer",
        -1
      );
      return;
    }

    nRequested = sqlite3_value_int64(argv[2]);
    if( nRequested<0 ){
      sqlite3_result_error(
        context,
        "alpa_string() length must not be negative",
        -1
      );
      return;
    }

    if( nRequested<nResult ){
      nResult = nRequested;
    }
  }

  iByteStart = alphabetUtf8ByteOffset(zAlphabet, iStart);
  iByteEnd = alphabetUtf8ByteOffset(zAlphabet, iStart + nResult);

  sqlite3_result_text(
    context,
    zAlphabet + iByteStart,
    iByteEnd - iByteStart,
    SQLITE_TRANSIENT
  );
}

#ifndef SQLITE_CORE
# define sqlite3AlphabetInit sqlite3AlphabetInit_Standalone
#endif

/*
** Register the extension's SQL functions.
**
** Three fixed arities are registered so SQLite itself rejects calls with
** zero arguments or more than three arguments.
*/
int sqlite3AlphabetInit(sqlite3 *db){
  static const int flags =
      SQLITE_UTF8
    | SQLITE_DETERMINISTIC
    | SQLITE_INNOCUOUS;
  int rc;

  rc = sqlite3_create_function(
    db, "alpa_string", 1, flags, 0,
    alphabetStringFunc, 0, 0
  );
  if( rc!=SQLITE_OK ) return rc;

  rc = sqlite3_create_function(
    db, "alpa_string", 2, flags, 0,
    alphabetStringFunc, 0, 0
  );
  if( rc!=SQLITE_OK ) return rc;

  return sqlite3_create_function(
    db, "alpa_string", 3, flags, 0,
    alphabetStringFunc, 0, 0
  );
}

#ifndef SQLITE_CORE
# if defined(_WIN32)
__declspec(dllexport)
# endif
int sqlite3_alphabet_init(
  sqlite3 *db,
  char **pzErrMsg,
  const sqlite3_api_routines *pApi
){
  (void)pzErrMsg;
  SQLITE_EXTENSION_INIT2(pApi);
  return sqlite3AlphabetInit(db);
}
#endif
