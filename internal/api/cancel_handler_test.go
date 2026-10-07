package api

import ("net/http"; "net/http/httptest"; "testing")

func TestCancelHandler(t *testing.T) { rr:=httptest.NewRecorder(); cancelHandler(rr,httptest.NewRequest(http.MethodPost,"/",nil)); if rr.Code!=http.StatusAccepted { t.Fatal("unexpected status") } }
