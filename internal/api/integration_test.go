package api

import ("net/http"; "net/http/httptest"; "testing"; "taskmesh/internal/queue"; "taskmesh/internal/storage")

func TestReady(t *testing.T) { s:=NewServer(storage.NewMemoryRepository(),queue.NewFIFO()); rr:=httptest.NewRecorder(); req:=httptest.NewRequest(http.MethodGet,"/ready",nil); s.Handler().ServeHTTP(rr,req); if rr.Code!=http.StatusOK { t.Fatalf("status=%d",rr.Code) } }
