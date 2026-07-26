/*
**
*/

#ifndef SQLITE_CORE
  #include "sqlite3ext.h"
  SQLITE_EXTENSION_INIT1
#else
  #include "sqlite3.h"
#endif


#ifndef SQLITE_CORE
# define sqlite3AlphabetInit sqlite3AlphabetInit_Standalone
#endif
int sqlite3AlphabetInit(sqlite3 *db){
  int rc;
  return rc;
}


#ifndef SQLITE_CORE
#ifdef _WIN32
__declspec(dllexport)
#endif
int sqlite3_alphabet_init(
  sqlite3 *db,
  char **pzErrMsg,
  const sqlite3_api_routines *pApi
){
  (void)pzErrMsg;  /* Unused */
  SQLITE_EXTENSION_INIT2(pApi);
  return sqlite3AlphabetInit(db);
}
#endif
