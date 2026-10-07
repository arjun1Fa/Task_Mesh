package dlq

import (
	"sync"
	"taskmesh/internal/core"
)

type Queue struct {
	mu    sync.Mutex
	items []Item
}

func NewQueue() *Queue { return &Queue{} }

func (q *Queue) Push(i Item) {
	q.mu.Lock()
	defer q.mu.Unlock()
	q.items = append(q.items, i)
}

func (q *Queue) List() []Item {
	q.mu.Lock()
	defer q.mu.Unlock()
	out := make([]Item, len(q.items))
	copy(out, q.items)
	for i := range out {
		out[i].Task = out[i].Task.Clone()
	}
	return out
}

func (q *Queue) Len() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	return len(q.items)
}

func (q *Queue) AddTask(t core.Task, attempts int, reason string) {
	q.Push(Item{Task: t.Clone(), Attempts: attempts, Reason: reason})
}
