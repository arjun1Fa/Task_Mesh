package storage

import (
	"errors"
	"taskmesh/internal/core"
)

// SQLiteRepository is the durable-storage seam used by the architecture.
// The default executable intentionally uses MemoryRepository so the project
// remains dependency-free; this adapter returns a clear error until a SQLite
// driver is selected by the deployment.
type SQLiteRepository struct {
	Path string
}

var ErrSQLiteNotImplemented = errors.New("sqlite repository adapter is not enabled in this build")

func NewSQLiteRepository(path string) *SQLiteRepository { return &SQLiteRepository{Path: path} }

func (r *SQLiteRepository) Create(_ core.Task) error { return ErrSQLiteNotImplemented }
func (r *SQLiteRepository) Save(_ core.Task) error   { return ErrSQLiteNotImplemented }
func (r *SQLiteRepository) Update(_ core.Task) error { return ErrSQLiteNotImplemented }
func (r *SQLiteRepository) Delete(_ string) error { return ErrSQLiteNotImplemented }
func (r *SQLiteRepository) Get(_ string) (core.Task, bool) {
	return core.Task{}, false
}
func (r *SQLiteRepository) List() []core.Task { return nil }
