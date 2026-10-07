package storage

import (
	"sort"
	"sync"
	"taskmesh/internal/core"
)

type MemoryRepository struct {
	mu    sync.RWMutex
	tasks map[string]core.Task
}

func NewMemoryRepository() *MemoryRepository {
	return &MemoryRepository{tasks: make(map[string]core.Task)}
}

func (r *MemoryRepository) Create(t core.Task) error {
	if err := t.Validate(); err != nil {
		return err
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.tasks[t.ID]; ok {
		return ErrAlreadyExists
	}
	r.tasks[t.ID] = t.Clone()
	return nil
}

func (r *MemoryRepository) Save(t core.Task) error {
	if err := t.Validate(); err != nil {
		return err
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	r.tasks[t.ID] = t.Clone()
	return nil
}

func (r *MemoryRepository) Update(t core.Task) error {
	if err := t.Validate(); err != nil {
		return err
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.tasks[t.ID]; !ok {
		return ErrNotFound
	}
	r.tasks[t.ID] = t.Clone()
	return nil
}

func (r *MemoryRepository) Delete(id string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.tasks[id]; !ok {
		return ErrNotFound
	}
	delete(r.tasks, id)
	return nil
}

func (r *MemoryRepository) Get(id string) (core.Task, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	t, ok := r.tasks[id]
	return t.Clone(), ok
}

func (r *MemoryRepository) List() []core.Task {
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := make([]core.Task, 0, len(r.tasks))
	for _, t := range r.tasks {
		out = append(out, t.Clone())
	}
	return out
}
