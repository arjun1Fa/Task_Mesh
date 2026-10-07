package worker

import (
	"errors"
	"sync"
)

var ErrExecutorAlreadyRegistered = errors.New("executor already registered")

// Registry maps task names to executable handlers.
type Registry struct {
	mu       sync.RWMutex
	handlers map[string]Executor
}

func NewRegistry() *Registry {
	return &Registry{handlers: make(map[string]Executor)}
}

func (r *Registry) Register(name string, e Executor) error {
	if name == "" || e == nil {
		return errors.New("executor name and handler are required")
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, exists := r.handlers[name]; exists {
		return ErrExecutorAlreadyRegistered
	}
	r.handlers[name] = e
	return nil
}

// MustRegister is intended for application startup where registration errors
// should stop bootstrapping rather than leave a partially configured runtime.
func (r *Registry) MustRegister(name string, e Executor) {
	if err := r.Register(name, e); err != nil {
		panic(err)
	}
}

func (r *Registry) Replace(name string, e Executor) error {
	if name == "" || e == nil {
		return errors.New("executor name and handler are required")
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	r.handlers[name] = e
	return nil
}

func (r *Registry) Get(name string) (Executor, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	e, ok := r.handlers[name]
	return e, ok
}
