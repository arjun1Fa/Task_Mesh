package worker

import ("context"; "errors"; "testing"; "taskmesh/internal/core")

type errorExecutor struct{}
func (errorExecutor) Execute(core.Task) error { return errors.New("boom") }

func TestRuntimeDispatch(t *testing.T) {
  out := Runtime{}.Dispatch(context.Background(),errorExecutor{},core.Task{ID:"x",Name:"x"})
  if out.Error==nil { t.Fatal("expected error") }
}
