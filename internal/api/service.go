package api

import (
	"context"
	"time"

	"taskmesh/internal/core"
	"taskmesh/internal/dlq"
	"taskmesh/internal/runtime"
	"taskmesh/internal/scheduler"
	"taskmesh/internal/storage"
)

// TaskService is the transport-independent contract exposed by the HTTP API.
type TaskService interface {
	Submit(context.Context, core.Task, string) (core.Task, bool, error)
	Get(string) (core.Task, bool)
	List() []core.Task
	Schedule(string, time.Time, time.Duration) (core.Task, error)
	Reschedule(string, time.Time) (core.Task, error)
	Cancel(string, string) (core.Task, error)
	PendingSchedules() []scheduler.Item
	WorkerCount() int
	QueueDepth() int
	Metrics() map[string]int
	ScaleWorkers(int)
	DLQ() []dlq.Item
	RecoverDLQ(dlq.Item) error
	Result(string) (core.TaskResult, bool)
}

type legacyService struct {
	repo  storage.TaskRepository
	queue interface {
		Enqueue(core.Task) error
	}
}

func (s legacyService) Submit(_ context.Context, t core.Task, _ string) (core.Task, bool, error) {
	if t.ID == "" {
		return core.Task{}, false, core.ErrTaskIDRequired
	}
	t = t.Normalized(time.Now().UTC())
	if err := s.repo.Save(t); err != nil {
		return core.Task{}, false, err
	}
	if err := s.queue.Enqueue(t); err != nil {
		return core.Task{}, false, err
	}
	return t, false, nil
}
func (s legacyService) Get(id string) (core.Task, bool) { return s.repo.Get(id) }
func (s legacyService) List() []core.Task { return s.repo.List() }
func (s legacyService) Schedule(_ string, _ time.Time, _ time.Duration) (core.Task, error) {
	return core.Task{}, runtime.ErrRuntimeStopped
}
func (s legacyService) Reschedule(_ string, _ time.Time) (core.Task, error) {
	return core.Task{}, runtime.ErrRuntimeStopped
}
func (s legacyService) Cancel(_ string, _ string) (core.Task, error) {
	return core.Task{}, runtime.ErrRuntimeStopped
}
func (s legacyService) PendingSchedules() []scheduler.Item { return nil }
func (s legacyService) WorkerCount() int { return 0 }
func (s legacyService) QueueDepth() int { return 0 }
func (s legacyService) Metrics() map[string]int { return map[string]int{} }
func (s legacyService) ScaleWorkers(_ int) {}
func (s legacyService) DLQ() []dlq.Item { return nil }
func (s legacyService) RecoverDLQ(_ dlq.Item) error { return runtime.ErrRuntimeStopped }
func (s legacyService) Result(_ string) (core.TaskResult, bool) { return core.TaskResult{}, false }
