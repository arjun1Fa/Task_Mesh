package retry

import ("context"; "taskmesh/internal/core"; "time")

type Runner struct { Policy Policy; Sleep func(time.Duration) }

func (r Runner) Run(ctx context.Context, task core.Task, fn func(core.Task) error) error {
  max := r.Policy.Attempts()
  for attempt:=1; attempt<=max; attempt++ {
    if err:=fn(task); err==nil { return nil } else if !ShouldRetry(attempt,max) { return ErrAttemptsExhausted }
    if r.Sleep!=nil { r.Sleep(Delay(r.Policy.BaseDelay,attempt)) }
    select { case <-ctx.Done(): return ctx.Err(); default: }
  }
  return ErrAttemptsExhausted
}
