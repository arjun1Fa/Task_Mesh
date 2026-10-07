package queue

import "taskmesh/internal/core"

type TaskQueue interface {
	Enqueue(core.Task) error
	Dequeue() (core.Task, bool)
	Len() int
}
