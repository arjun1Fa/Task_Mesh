package queue

import (
	"context"
	"testing"
	"taskmesh/internal/core"
	"time"
)

func TestPriorityQueueOrdersByPriority(t *testing.T) {
	q := NewPriorityQueue()
	_ = q.Enqueue(core.Task{ID: "low", Name: "x", Priority: 1})
	_ = q.Enqueue(core.Task{ID: "high", Name: "x", Priority: 10})
	_ = q.Enqueue(core.Task{ID: "same", Name: "x", Priority: 10})

	first, _ := q.Dequeue()
	second, _ := q.Dequeue()
	third, _ := q.Dequeue()
	if first.ID != "high" || second.ID != "same" || third.ID != "low" {
		t.Fatalf("unexpected order: %s %s %s", first.ID, second.ID, third.ID)
	}
}

func TestPriorityQueueWaitsForWork(t *testing.T) {
	q := NewPriorityQueue()
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()
	done := make(chan core.Task, 1)
	go func() {
		t, ok := q.DequeueContext(ctx)
		if ok { done <- t }
	}()
	_ = q.Enqueue(core.Task{ID: "wake", Name: "x"})
	select {
	case got := <-done:
		if got.ID != "wake" { t.Fatal("wrong task") }
	case <-ctx.Done():
		t.Fatal("queue did not wake")
	}
}
