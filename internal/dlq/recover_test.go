package dlq

import ("testing"; "taskmesh/internal/core")

func TestRecover(t *testing.T) { got:=Recover(Item{Task:core.Task{ID:"x"}}); if got.ID!="x" { t.Fatal("recovery failed") } }
