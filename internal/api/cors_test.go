package api

import ("net/http"; "net/http/httptest"; "testing")

func TestCORS(t *testing.T) { rr:=httptest.NewRecorder(); cors(http.HandlerFunc(func(http.ResponseWriter,*http.Request){})).ServeHTTP(rr,httptest.NewRequest(http.MethodGet,"/",nil)); if rr.Header().Get("Access-Control-Allow-Origin")=="" { t.Fatal("cors header missing") } }
