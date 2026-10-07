package worker

import "taskmesh/internal/core"

func SafeExecute(e Executor, t core.Task) (err error) {
  defer func() { if recover() != nil { err = ErrExecutorPanic } }()
  return e.Execute(t)
}
