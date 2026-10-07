package queue

import (
	"context"
	"taskmesh/internal/core"
)

// BlockingTaskQueue is the optional queue capability used by managed workers.
// Implementations must also satisfy TaskQueue.
type BlockingTaskQueue interface {
	TaskQueue
	DequeueContext(context.Context) (core.Task, bool)
}
