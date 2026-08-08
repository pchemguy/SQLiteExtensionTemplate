/*
** alphabet_api.h
**
** This declaration catalogue is included by alphabet.h, which supplies
** AB_TEST_API and AB_TEST_DATA_API, and is not an independent C client header.
**
*/

#ifndef ALPHABET_API_H
#define ALPHABET_API_H

/*
** Return the number of bytes occupied by the UTF-8 code point beginning at
** zText.
**
** Parameters:
**   zText
**     IN, non-NULL pointer to the first byte of a UTF-8 code point.
**
** Returns:
**   1, 2, 3, or 4 according to the leading-byte pattern.
**
** Preconditions:
**   zText must point to readable memory containing at least the first byte of
**   a UTF-8 code point.
**
** Notes:
**   This function classifies only the leading byte. It does not validate the
**   complete UTF-8 sequence, continuation bytes, overlong encodings, Unicode
**   range, or termination.
*/
AB_TEST_API int ab_utf8_byte_count(const char *zText);

/*
** Return the number of Unicode code points in a NUL-terminated UTF-8 string.
**
** Parameters:
**   zText
**     IN, non-NULL pointer to a NUL-terminated valid UTF-8 byte string.
**
** Returns:
**   Number of UTF-8 code points preceding the terminating NUL.
**   The empty string returns 0.
**
** Preconditions:
**   zText must be non-NULL, NUL-terminated, and contain UTF-8 sequences whose
**   leading bytes correctly describe their byte lengths.
**
** Notes:
**   The function advances through the string using ab_utf8_byte_count() and
**   therefore does not independently validate UTF-8.
**
** Ownership:
**   zText is borrowed and is neither retained nor modified.
*/
AB_TEST_API int64_t ab_utf8_length(const char *zText);

/*
** Return the byte offset of Unicode code-point index i within a NUL-terminated
** UTF-8 string.
**
** Parameters:
**   zText
**     IN, non-NULL pointer to a NUL-terminated valid UTF-8 byte string.
**
**   i
**     IN code-point index in the inclusive range
**
**         0 <= i <= ab_utf8_length(zText)
**
** Returns:
**   Byte offset from zText to code-point index i.
**
**   For i == 0, returns 0.
**   For i == ab_utf8_length(zText), returns the byte length of the string,
**   i.e. the offset of the terminating NUL.
**
** Preconditions:
**   The caller must satisfy the range constraint for i. Negative or
**   out-of-range values are outside this function's contract.
**
**   The resulting byte offset must be representable as int.
**
** Notes:
**   Index and length are measured in Unicode code points; the return value is
**   measured in bytes.
**
** Ownership:
**   zText is borrowed and is neither retained nor modified.
*/
AB_TEST_API int ab_utf8_byte_offset(const char *zText, int64_t i);

/*
** Resolve a language name to the corresponding built-in UTF-8 alphabet.
**
** Parameters:
**   zLanguage
**     IN, non-NULL pointer to a NUL-terminated string.
**
** Accepted values:
**   "en"      or "English"  -> Latin alphabet
**   "ru"      or "Russian"  -> Russian Cyrillic alphabet
**
**   Matching is case-insensitive according to sqlite3_stricmp().
**
** Returns:
**   Non-NULL pointer to the selected NUL-terminated UTF-8 alphabet string when
**   zLanguage is recognized; NULL otherwise.
**
** Preconditions:
**   zLanguage must be non-NULL and NUL-terminated.
**
** Ownership:
**   The returned string is borrowed static storage owned by the library.
**   The caller must not modify or free it.
**
** Lifetime:
**   A successful return remains valid for the lifetime of the library.
**
** Side effects:
**   None.
*/
AB_TEST_API const char *ab_alphabet_select(const char *zLanguage);

#endif /* ALPHABET_API_H */
