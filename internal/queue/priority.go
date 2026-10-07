package queue

import (
	"container/heap"
	"context"
	"sync"
	"taskmesh/internal/core"
)

type priorityItem struct {
	task  core.Task
	order uint64
	index int
}

type priorityHeap []*priorityItem

func (h priorityHeap) Len() int { return len(h) }
func (h priorityHeap) Less(i, j int) bool {
	if h[i].task.Priority == h[j].task.Priority {
		return h[i].order < h[j].order
	}
	return h[i].task.Priority > h[j].task.Priority
}
func (h priorityHeap) Swap(i, j int) {
	h[i], h[j] = h[j], h[i]
	h[i].index = i
	h[j].index = j
}
func (h *priorityHeap) Push(x any) {
	item := x.(*priorityItem)
	item.index = len(*h)
	*h = append(*h, item)
}
func (h *priorityHeap) Pop() any {
	old := *h
	n := len(old)
	item := old[n-1]
	old[n-1] = nil
	item.index = -1
	*h = old[:n-1]
	return item
}

// PriorityQueue dequeues higher-priority tasks first while preserving FIFO
// ordering among tasks that have the same priority.
type PriorityQueue struct {
	mu    sync.Mutex
	items priorityHeap
	wake  chan struct{}
	order uint64
}

func NewPriorityQueue() *PriorityQueue {
	q := &PriorityQueue{wake: make(chan struct{}, 1)}
	heap.Init(&q.items)
	return q
}

func (q *PriorityQueue) Enqueue(t core.Task) error {
	if err := t.Validate(); err != nil {
		return err
	}
	q.mu.Lock()
	q.order++
	heap.Push(&q.items, &priorityItem{task: t.Clone(), order: q.order})
	q.mu.Unlock()
	select {
	case q.wake <- struct{}{}:
	default:
	}
	return nil
}

func (q *PriorityQueue) Dequeue() (core.Task, bool) {
	q.mu.Lock()
	defer q.mu.Unlock()
	if len(q.items) == 0 {
		return core.Task{}, false
	}
	return heap.Pop(&q.items).(*priorityItem).task, true
}

func (q *PriorityQueue) DequeueContext(ctx context.Context) (core.Task, bool) {
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

func (q *PriorityQueue) Len() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	return len(q.items)
}
