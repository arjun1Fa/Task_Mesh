package api

import (
	"encoding/json"
	"net/http"
	"strings"
)

func (s *Server) schedulesV1(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	items := s.service.PendingSchedules()
	writeJSON(w, http.StatusOK, map[string]any{"count": len(items), "items": items})
}

func (s *Server) workersV1(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		writeJSON(w, http.StatusOK, map[string]int{"workers": s.service.WorkerCount()})
	case http.MethodPost:
		var body struct { Workers int `json:"workers"` }
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Workers < 1 {
			writeError(w, http.StatusBadRequest, "workers must be a positive integer")
			return
		}
		s.service.ScaleWorkers(body.Workers)
		writeJSON(w, http.StatusOK, map[string]int{"workers": s.service.WorkerCount()})
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (s *Server) dlqV1(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		items := s.service.DLQ()
		writeJSON(w, http.StatusOK, map[string]any{"count": len(items), "items": items})
		return
	}
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	var body struct {
		TaskID string `json:"task_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || strings.TrimSpace(body.TaskID) == "" {
		writeError(w, http.StatusBadRequest, "task_id is required")
		return
	}
	for _, item := range s.service.DLQ() {
		if item.Task.ID == body.TaskID {
			if err := s.service.RecoverDLQ(item); err != nil {
				writeError(w, http.StatusBadRequest, err.Error())
				return
			}
			writeJSON(w, http.StatusAccepted, map[string]string{"status": "requeued", "task_id": body.TaskID})
			return
		}
	}
	writeError(w, http.StatusNotFound, "dead-letter task not found")
}

func (s *Server) resultV1(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	runID := strings.TrimPrefix(r.URL.Path, "/v1/results/")
	if runID == "" {
		writeError(w, http.StatusBadRequest, "run id is required")
		return
	}
	result, ok := s.service.Result(runID)
	if !ok {
		writeError(w, http.StatusNotFound, "result not found")
		return
	}
	writeJSON(w, http.StatusOK, result)
}


func (s *Server) metricsV1(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	writeJSON(w, http.StatusOK, s.service.Metrics())
}
