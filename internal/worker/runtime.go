package worker

import ("context"; "taskmesh/internal/core")

type Runtime struct { QueueLen func() int }

func (r Runtime) Dispatch(ctx context.Context, executor Executor, task core.Task) Result {
  select {
  case <-ctx.Done(): return Result{TaskID:task.ID, Error:ctx.Err()}
  default: return Result{TaskID:task.ID, Error:SafeExecute(executor,task)}
  }
}
