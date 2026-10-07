package worker

import ("testing"; "taskmesh/internal/core")

type noopExecutor struct{}
func (noopExecutor) Execute(core.Task) error { return nil }

func TestRegistry(t *testing.T) {
  r:=NewRegistry(); r.Register("noop",noopExecutor{})
  if _,ok:=r.Get("noop"); !ok { t.Fatal("missing executor") }
}
