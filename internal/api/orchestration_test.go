package api

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"taskmesh/internal/core"
	taskruntime "taskmesh/internal/runtime"
	"taskmesh/internal/storage"
	"taskmesh/internal/worker"
)

func testRuntime(t *testing.T) *taskruntime.Runtime {
	t.Helper()
	repo := storage.NewMemoryRepository()
	reg := worker.NewRegistry()
	reg.MustRegister("log", worker.ExecutorFunc(func(core.Task) error { return nil }))
	r := taskruntime.New(repo, nil, reg, taskruntime.Config{WorkerCount: 1, SchedulerPoll: 5 * time.Millisecond})
	if err := r.Start(context.Background()); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(r.Stop)
	return r
}

func TestRuntimeTaskAPIGeneratesID(t *testing.T) {
	r := testRuntime(t)
	s := NewRuntimeServer(r)
	req := httptest.NewRequest(http.MethodPost, "/v1/tasks", strings.NewReader(`{"name":"log","payload":{"hello":"world"}}`))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()

	s.Handler().ServeHTTP(rr, req)
	if rr.Code != http.StatusCreated {
		t.Fatalf("status=%d body=%s", rr.Code, rr.Body.String())
	}
	var body map[string]any
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body["id"] == "" {
		t.Fatal("expected generated id")
	}
}

func TestRuntimeWorkerScaleAPI(t *testing.T) {
	r := testRuntime(t)
	s := NewRuntimeServer(r)
	req := httptest.NewRequest(http.MethodPost, "/v1/workers", strings.NewReader(`{"workers":3}`))
	rr := httptest.NewRecorder()

	s.Handler().ServeHTTP(rr, req)
	if rr.Code != http.StatusOK {
		t.Fatalf("status=%d", rr.Code)
	}
	if r.WorkerCount() != 3 {
		t.Fatalf("workers=%d", r.WorkerCount())
	}
}

func TestRuntimeScheduleAPI(t *testing.T) {
	r := testRuntime(t)
	s := NewRuntimeServer(r)

	create := httptest.NewRequest(http.MethodPost, "/v1/tasks", strings.NewReader(`{"name":"log"}`))
	create.Header.Set("Content-Type", "application/json")
	created := httptest.NewRecorder()
	s.Handler().ServeHTTP(created, create)
	if created.Code != http.StatusCreated {
		t.Fatalf("create status=%d", created.Code)
	}
	var task map[string]any
	_ = json.Unmarshal(created.Body.Bytes(), &task)
	id := task["id"].(string)

	at := time.Now().Add(time.Second).UTC().Format(time.RFC3339)
	body := `{"scheduled_at":"` + at + `"}`
	req := httptest.NewRequest(http.MethodPost, "/v1/tasks/"+id+"/schedule", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	s.Handler().ServeHTTP(rr, req)
	if rr.Code != http.StatusOK {
		t.Fatalf("schedule status=%d body=%s", rr.Code, rr.Body.String())
	}
}
