package api

import ("net/http"; "net/http/httptest"; "testing")

func TestIdempotencyHeader(t *testing.T) {
  r:=httptest.NewRequest(http.MethodPost,"/tasks",nil); r.Header.Set("Idempotency-Key","abc")
  if idempotencyHeader(r)!="abc" { t.Fatal("header not read") }
}
