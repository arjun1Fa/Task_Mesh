package api

import ("net/http"; "net/http/httptest"; "testing")

func TestBodyLimitMiddleware(t *testing.T) { next:=http.HandlerFunc(func(w http.ResponseWriter,_ *http.Request){w.WriteHeader(http.StatusNoContent)}); rr:=httptest.NewRecorder(); withBodyLimit(next).ServeHTTP(rr,httptest.NewRequest(http.MethodGet,"/",nil)); if rr.Code!=http.StatusNoContent { t.Fatal("middleware failed") } }
