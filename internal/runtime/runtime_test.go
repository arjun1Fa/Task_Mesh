package runtime

import (
	"context"
	"testing"
	"time"

	"taskmesh/internal/core"
	"taskmesh/internal/retry"
	"taskmesh/internal/storage"
	"taskmesh/internal/worker"
)

func TestRuntimeExecutesRegisteredTask(t *testing.T) {
	repo := storage.NewMemoryRepository()
	reg := worker.NewRegistry()
	done := make(chan struct{}, 1)
	if err := reg.Register("echo", worker.ExecutorFunc(func(core.Task) error {
		done <- struct{}{}
		return nil
	})); err != nil {
		t.Fatal(err)
	}
	r := New(repo, nil, reg, Config{WorkerCount: 1})
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	if err := r.Start(ctx); err != nil {
		t.Fatal(err)
	}
	task, _, err := r.Submit(ctx, core.Task{Name: "echo"}, "")
	if err != nil {
		t.Fatal(err)
	}
	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("task was not executed")
	}
	got, ok := repo.Get(task.ID)
	if !ok || got.Status != core.StatusSucceeded {
		t.Fatalf("unexpected task state: %#v", got)
	}
	r.Stop()
}

func TestRuntimeMissingExecutorGoesToDLQ(t *testing.T) {
	repo := storage.NewMemoryRepository()
	r := New(repo, nil, worker.NewRegistry(), Config{
		WorkerCount: 1,
		Retry: retry.Policy{MaxAttempts: 1, BaseDelay: time.Millisecond},
	})
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	_ = r.Start(ctx)
	_, _, err := r.Submit(ctx, core.Task{Name: "missing"}, "")
	if err != nil {
		t.Fatal(err)
	}
	select {
	case <-time.After(250 * time.Millisecond):
		if r.dlq.Len() == 0 {
			t.Fatal("expected dead-letter task")
		}
	}
	r.Stop()
}

func TestRuntimeCancelScheduledTask(t *testing.T) {
	repo := storage.NewMemoryRepository()
	r := New(repo, nil, worker.NewRegistry(), Config{WorkerCount: 1})
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	_ = r.Start(ctx)
	at := time.Now().Add(time.Hour)
	task, _, err := r.Submit(ctx, core.Task{Name: "later", ScheduledAt: &at}, "")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := r.Cancel(task.ID, "test"); err != nil {
		t.Fatal(err)
	}
	got, _ := repo.Get(task.ID)
	if got.Status != core.StatusCanceled {
		t.Fatalf("unexpected state: %#v", got)
	}
	r.Stop()
}

func TestRuntimeRecurringTaskRunsMoreThanOnce(t *testing.T) {
	repo := storage.NewMemoryRepository()
	reg := worker.NewRegistry()
	runs := make(chan struct{}, 4)
	if err := reg.Register("tick", worker.ExecutorFunc(func(core.Task) error {
		runs <- struct{}{}
		return nil
	})); err != nil {
		t.Fatal(err)
	}
	r := New(repo, nil, reg, Config{WorkerCount: 1, SchedulerPoll: 5 * time.Millisecond})
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	_ = r.Start(ctx)
	at := time.Now().Add(10 * time.Millisecond)
	task, _, err := r.Submit(ctx, core.Task{Name: "tick", ScheduledAt: &at, RepeatEvery: 15 * time.Millisecond}, "")
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 2; i++ {
		select {
		case <-runs:
		case <-time.After(time.Second):
			t.Fatalf("recurring task fired only %d times", i)
		}
	}
	updated, ok := repo.Get(task.ID)
	if !ok || updated.Status != core.StatusScheduled {
		t.Fatalf("unexpected recurring state: %#v", updated)
	}
	r.Stop()
}
