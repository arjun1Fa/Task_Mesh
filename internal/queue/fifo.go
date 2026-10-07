package queue

import (
	"context"
	"sync"
	"taskmesh/internal/core"
)

// FIFO is a thread-safe in-memory queue. Dequeue is non-blocking for
// compatibility, while DequeueContext waits efficiently for work.
type FIFO struct {
	mu    sync.Mutex
	tasks []core.Task
	wake  chan struct{}
}

func NewFIFO() *FIFO { return &FIFO{wake: make(chan struct{}, 1)} }

func (q *FIFO) Enqueue(t core.Task) error {
	if err := t.Validate(); err != nil {
		return err
	}
	q.mu.Lock()
	q.tasks = append(q.tasks, t.Clone())
	q.mu.Unlock()
	select {
	case q.wake <- struct{}{}:
	default:
	}
	return nil
}

func (q *FIFO) Dequeue() (core.Task, bool) {
	q.mu.Lock()
	defer q.mu.Unlock()
	if len(q.tasks) == 0 {
		return core.Task{}, false
	}
	t := q.tasks[0]
	q.tasks[0] = core.Task{}
	q.tasks = q.tasks[1:]
	return t, true
}

// DequeueContext blocks until a task is available or ctx is canceled.
func (q *FIFO) DequeueContext(ctx context.Context) (core.Task, bool) {
	for {
		if t, ok := q.Dequeue(); ok {
			return t, true
		}
		select {
		case <-ctx.Done():
			return core.Task{}, false
		case <-q.wake:
		}
	}
}

func (q *FIFO) Len() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	return len(q.tasks)
}
