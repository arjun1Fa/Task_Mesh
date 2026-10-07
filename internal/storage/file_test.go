package storage

import (
	"path/filepath"
	"testing"
	"taskmesh/internal/core"
	"time"
)

func TestFileRepositoryPersistsTaskState(t *testing.T) {
	path := filepath.Join(t.TempDir(), "tasks.json")
	r, err := NewFileRepository(path)
	if err != nil {
		t.Fatal(err)
	}
	tm := time.Now().UTC().Truncate(time.Second)
	task := core.Task{ID: "persisted", Name: "demo", CreatedAt: tm, Status: core.StatusQueued}
	if err := r.Save(task); err != nil {
		t.Fatal(err)
	}
	reloaded, err := NewFileRepository(path)
	if err != nil {
		t.Fatal(err)
	}
	got, ok := reloaded.Get("persisted")
	if !ok || got.Name != "demo" || !got.CreatedAt.Equal(tm) {
		t.Fatalf("unexpected task after reload: %#v", got)
	}
}
