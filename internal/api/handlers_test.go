package api

import ("net/http"; "net/http/httptest"; "strings"; "testing"; "taskmesh/internal/queue"; "taskmesh/internal/storage")

func TestHealth(t *testing.T) { s:=NewServer(storage.NewMemoryRepository(),queue.NewFIFO()); rr:=httptest.NewRecorder(); req:=httptest.NewRequest(http.MethodGet,"/health",nil); s.Handler().ServeHTTP(rr,req); if rr.Code!=http.StatusOK { t.Fatalf("status=%d",rr.Code) } }
func TestCreateTaskRejectsEmptyPayload(t *testing.T) { s:=NewServer(storage.NewMemoryRepository(),queue.NewFIFO()); rr:=httptest.NewRecorder(); req:=httptest.NewRequest(http.MethodPost,"/tasks",strings.NewReader(`{}`)); s.Handler().ServeHTTP(rr,req); if rr.Code!=http.StatusBadRequest { t.Fatalf("status=%d",rr.Code) } }
