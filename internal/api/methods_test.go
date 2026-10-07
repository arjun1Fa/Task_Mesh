package api

import ("net/http"; "net/http/httptest"; "testing")

func TestSupportsMethod(t *testing.T) { r:=httptest.NewRequest(http.MethodGet,"/",nil); if !supportsMethod(r,http.MethodGet){t.Fatal("method mismatch")} }
