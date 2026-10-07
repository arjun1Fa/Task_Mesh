package api

import "net/http"

func (s *Server) routes() {
	s.mux.HandleFunc("/health", s.health)
	s.mux.HandleFunc("/ready", s.ready)
	s.mux.HandleFunc("/tasks", s.tasks)
	s.mux.HandleFunc("/task", s.taskByID)

	s.mux.HandleFunc("/v1/tasks", s.tasksV1)
	s.mux.HandleFunc("/v1/tasks/", s.taskActionV1)
	s.mux.HandleFunc("/v1/schedules", s.schedulesV1)
	s.mux.HandleFunc("/v1/workers", s.workersV1)
	s.mux.HandleFunc("/v1/dlq", s.dlqV1)
	s.mux.HandleFunc("/v1/results/", s.resultV1)
	s.mux.HandleFunc("/v1/metrics", s.metricsV1)
}
