package worker

import (
	"context"
	"taskmesh/internal/core"
)

// Executor executes a single task. Returning an error marks the execution
// as failed and allows the runtime retry policy to decide what happens next.
type Executor interface {
	Execute(core.Task) error
}

// ExecutorFunc adapts a function to the Executor interface.
type ExecutorFunc func(core.Task) error

func (f ExecutorFunc) Execute(t core.Task) error { return f(t) }

// ContextExecutor is an optional capability. Handlers that implement it
// receive the runtime timeout/cancellation context.
type ContextExecutor interface {
	ExecuteContext(context.Context, core.Task) error
}

// ContextExecutorFunc adapts a context-aware function to ContextExecutor.
type ContextExecutorFunc func(context.Context, core.Task) error

func (f ContextExecutorFunc) ExecuteContext(ctx context.Context, t core.Task) error {
	return f(ctx, t)
}
