package storage

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"taskmesh/internal/core"
)

var ErrEmptyDataPath = errors.New("data file path is required")

// FileRepository provides small-deployment durability without adding a
// database dependency. Each mutation is written atomically to a JSON file.
// It is intended for development, demos and single-node deployments.
type FileRepository struct {
	mu    sync.RWMutex
	path  string
	tasks map[string]core.Task
}

func NewFileRepository(path string) (*FileRepository, error) {
	if path == "" {
		return nil, ErrEmptyDataPath
	}
	r := &FileRepository{path: path, tasks: make(map[string]core.Task)}
	if err := r.load(); err != nil {
		return nil, err
	}
	return r, nil
}

func (r *FileRepository) Create(t core.Task) error {
	if err := t.Validate(); err != nil {
		return err
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.tasks[t.ID]; ok {
		return ErrAlreadyExists
	}
	r.tasks[t.ID] = t.Clone()
	return r.flushLocked()
}

func (r *FileRepository) Save(t core.Task) error {
	if err := t.Validate(); err != nil {
		return err
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	r.tasks[t.ID] = t.Clone()
	return r.flushLocked()
}

func (r *FileRepository) Update(t core.Task) error {
	if err := t.Validate(); err != nil {
		return err
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.tasks[t.ID]; !ok {
		return ErrNotFound
	}
	r.tasks[t.ID] = t.Clone()
	return r.flushLocked()
}

func (r *FileRepository) Delete(id string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.tasks[id]; !ok {
		return ErrNotFound
	}
	delete(r.tasks, id)
	return r.flushLocked()
}

func (r *FileRepository) Get(id string) (core.Task, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	t, ok := r.tasks[id]
	return t.Clone(), ok
}

func (r *FileRepository) List() []core.Task {
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := make([]core.Task, 0, len(r.tasks))
	for _, t := range r.tasks {
		out = append(out, t.Clone())
	}
	sort.Slice(out, func(i, j int) bool {
		return out[i].CreatedAt.Before(out[j].CreatedAt)
	})
	return out
}

func (r *FileRepository) load() error {
	r.mu.Lock()
	defer r.mu.Unlock()
	data, err := os.ReadFile(r.path)
	if errors.Is(err, os.ErrNotExist) {
		return nil
	}
	if err != nil {
		return err
	}
	if len(data) == 0 {
		return nil
	}
	var tasks []core.Task
	if err := json.Unmarshal(data, &tasks); err != nil {
		return err
	}
	for _, t := range tasks {
		r.tasks[t.ID] = t
	}
	return nil
}

func (r *FileRepository) flushLocked() error {
	if dir := filepath.Dir(r.path); dir != "." {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return err
		}
	}
	tasks := make([]core.Task, 0, len(r.tasks))
	for _, t := range r.tasks {
		tasks = append(tasks, t.Clone())
	}
	sort.Slice(tasks, func(i, j int) bool { return tasks[i].CreatedAt.Before(tasks[j].CreatedAt) })
	data, err := json.MarshalIndent(tasks, "", "  ")
	if err != nil {
		return err
	}
	tmp := r.path + ".tmp"
	if err := os.WriteFile(tmp, data, 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, r.path)
}
