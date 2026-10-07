package api

import (
	"net/http"

	"taskmesh/internal/queue"
	"taskmesh/internal/storage"
)

// Server exposes the TaskMesh HTTP API.
type Server struct {
	service TaskService
	mux     *http.ServeMux
}

// NewServer preserves the original constructor for lightweight tests.
// Production applications should use NewRuntimeServer.
func NewServer(repo storage.TaskRepository, q queue.TaskQueue) *Server {
	s := &Server{
		service: legacyService{repo: repo, queue: q},
		mux:     http.NewServeMux(),
	}
	s.routes()
	return s
}

// NewRuntimeServer binds the HTTP transport to the complete managed runtime.
func NewRuntimeServer(service TaskService) *Server {
	s := &Server{service: service, mux: http.NewServeMux()}
	s.routes()
	return s
}

func (s *Server) Handler() http.Handler {
	return chain(logging(s.mux))
}
