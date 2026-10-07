package auth

import ("net/http"; "net/http/httptest"; "testing")

func TestMiddlewareRejectsEmptyHeader(t *testing.T) { h:=Middleware(http.HandlerFunc(func(http.ResponseWriter,*http.Request){}),func(v string)bool{return v!=""}); rr:=httptest.NewRecorder(); h.ServeHTTP(rr,httptest.NewRequest(http.MethodGet,"/",nil)); if rr.Code!=http.StatusUnauthorized { t.Fatal("expected unauthorized") } }
