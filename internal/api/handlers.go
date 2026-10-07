package api

import (
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"taskmesh/internal/core"
)

type taskRequest struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	Payload     json.RawMessage   `json:"payload"`
	ScheduledAt string            `json:"scheduled_at"`
	RepeatEvery string            `json:"repeat_every"`
	MaxAttempts int               `json:"max_attempts"`
	Timeout     string            `json:"timeout"`
	Priority    int               `json:"priority"`
	Metadata    map[string]string `json:"metadata"`
}

type taskResponse struct {
	ID          string            `json:"id"`
	RunID       string            `json:"run_id,omitempty"`
	Name        string            `json:"name"`
	Payload     json.RawMessage   `json:"payload,omitempty"`
	CreatedAt   time.Time         `json:"created_at"`
	Status      core.Status       `json:"status"`
	ScheduledAt string            `json:"scheduled_at,omitempty"`
	RepeatEvery string            `json:"repeat_every,omitempty"`
	MaxAttempts int               `json:"max_attempts"`
	Timeout     string            `json:"timeout,omitempty"`
	Priority    int               `json:"priority"`
	Metadata    map[string]string `json:"metadata,omitempty"`
}

func (s *Server) health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) ready(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"status": "ready", "workers": s.service.WorkerCount()})
}

func (s *Server) tasks(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		tasks := s.service.List()
		out := make([]taskResponse, 0, len(tasks))
		for _, task := range tasks {
			out = append(out, toTaskResponse(task))
		}
		writeJSON(w, http.StatusOK, out)
		return
	}
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	req, err := decodeTaskRequest(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	t, err := req.task()
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	out, duplicate, err := s.service.Submit(r.Context(), t, r.Header.Get("Idempotency-Key"))
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	status := http.StatusCreated
	if duplicate {
		status = http.StatusOK
	}
	writeJSON(w, status, toTaskResponse(out))
}

func (s *Server) taskByID(w http.ResponseWriter, r *http.Request) {
	id := pathID(r)
	if id == "" {
		writeError(w, http.StatusBadRequest, "id is required")
		return
	}
	t, ok := s.service.Get(id)
	if !ok {
		writeError(w, http.StatusNotFound, "task not found")
		return
	}
	writeJSON(w, http.StatusOK, toTaskResponse(t))
}

func (s *Server) tasksV1(w http.ResponseWriter, r *http.Request) {
	s.tasks(w, r)
}

func (s *Server) taskActionV1(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/v1/tasks/")
	parts := strings.Split(strings.Trim(path, "/"), "/")
	if len(parts) == 0 || parts[0] == "" {
		writeError(w, http.StatusBadRequest, "task id is required")
		return
	}
	id := parts[0]
	if len(parts) == 1 {
		if r.Method != http.MethodGet {
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}
		t, ok := s.service.Get(id)
		if !ok {
			writeError(w, http.StatusNotFound, "task not found")
			return
		}
		writeJSON(w, http.StatusOK, toTaskResponse(t))
		return
	}
	if len(parts) != 2 {
		writeError(w, http.StatusNotFound, "unknown task route")
		return
	}

	switch parts[1] {
	case "cancel":
		s.cancelTask(w, r, id)
	case "schedule":
		s.scheduleTask(w, r, id, false)
	case "reschedule":
		s.scheduleTask(w, r, id, true)
	default:
		writeError(w, http.StatusNotFound, "unknown task action")
	}
}

func (s *Server) cancelTask(w http.ResponseWriter, r *http.Request, id string) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	var body struct { Reason string `json:"reason"` }
	if r.Body != nil {
		_ = json.NewDecoder(r.Body).Decode(&body)
	}
	t, err := s.service.Cancel(id, body.Reason)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, toTaskResponse(t))
}

func (s *Server) scheduleTask(w http.ResponseWriter, r *http.Request, id string, onlyReschedule bool) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	var body struct {
		ScheduledAt string `json:"scheduled_at"`
		RepeatEvery string `json:"repeat_every"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	at, err := time.Parse(time.RFC3339, body.ScheduledAt)
	if err != nil {
		writeError(w, http.StatusBadRequest, "scheduled_at must be RFC3339")
		return
	}
	if onlyReschedule {
		t, err := s.service.Reschedule(id, at)
		if err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, toTaskResponse(t))
		return
	}
	var repeat time.Duration
	if body.RepeatEvery != "" {
		repeat, err = time.ParseDuration(body.RepeatEvery)
		if err != nil || repeat <= 0 {
			writeError(w, http.StatusBadRequest, "repeat_every must be a positive duration")
			return
		}
	}
	t, err := s.service.Schedule(id, at, repeat)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, toTaskResponse(t))
}

func decodeTaskRequest(r *http.Request) (taskRequest, error) {
	var req taskRequest
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&req); err != nil {
		return req, err
	}
	return req, nil
}

func (r taskRequest) task() (core.Task, error) {
	t := core.Task{
		ID: r.ID, Name: strings.TrimSpace(r.Name), Payload: append([]byte(nil), r.Payload...),
		MaxAttempts: r.MaxAttempts, Priority: r.Priority, Metadata: r.Metadata,
	}
	if r.ScheduledAt != "" {
		at, err := time.Parse(time.RFC3339, r.ScheduledAt)
		if err != nil {
			return core.Task{}, err
		}
		t.ScheduledAt = &at
	}
	if r.RepeatEvery != "" {
		d, err := time.ParseDuration(r.RepeatEvery)
		if err != nil {
			return core.Task{}, err
		}
		t.RepeatEvery = d
	}
	if r.Timeout != "" {
		d, err := time.ParseDuration(r.Timeout)
		if err != nil {
			return core.Task{}, err
		}
		t.Timeout = d
	}
	return t, t.ValidateDefinition()
}

func toTaskResponse(t core.Task) taskResponse {
	out := taskResponse{
		ID: t.ID, RunID: t.RunID, Name: t.Name, CreatedAt: t.CreatedAt,
		Status: t.Status, MaxAttempts: t.MaxAttempts, Priority: t.Priority,
		Metadata: t.Metadata,
	}
	if len(t.Payload) > 0 {
		out.Payload = json.RawMessage(append([]byte(nil), t.Payload...))
	}
	if t.ScheduledAt != nil {
		out.ScheduledAt = t.ScheduledAt.UTC().Format(time.RFC3339)
	}
	if t.RepeatEvery > 0 {
		out.RepeatEvery = t.RepeatEvery.String()
	}
	if t.Timeout > 0 {
		out.Timeout = t.Timeout.String()
	}
	return out
}
