package worker

import ("context"; "taskmesh/internal/core"; "taskmesh/internal/retry")

func ExecuteWithRetry(ctx context.Context, t core.Task, e Executor, p retry.Policy) error {
  return (retry.Runner{Policy:p}).Run(ctx,t,func(task core.Task)error{return e.Execute(task)})
}
