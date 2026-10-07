package storage

import "taskmesh/internal/core"

// TaskRepository stores durable task state.
// Create is the atomic admission operation used for new logical tasks.
// Save remains an upsert for compatibility with the original prototype.
type TaskRepository interface {
	Create(core.Task) error
	Save(core.Task) error
	Update(core.Task) error
	Delete(string) error
	Get(string) (core.Task, bool)
	List() []core.Task
}
