package core

import "testing"

func TestTaskResultDefaults(t *testing.T) {
  r:=TaskResult{TaskID:"x"}
  if r.Started || r.Finished { t.Fatal("unexpected state") }
}
