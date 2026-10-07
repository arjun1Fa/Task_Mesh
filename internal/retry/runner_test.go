package retry

import ("context"; "testing"; "taskmesh/internal/core"; "time")

func TestRunnerSucceedsAfterRetry(t *testing.T) {
  n:=0
  r:=Runner{Policy:Policy{MaxAttempts:3,BaseDelay:time.Millisecond},Sleep:func(time.Duration){}}
  err:=r.Run(context.Background(),core.Task{ID:"x"},func(core.Task)error{ n++; if n<3{return context.DeadlineExceeded}; return nil })
  if err!=nil || n!=3 { t.Fatalf("err=%v attempts=%d",err,n) }
}
