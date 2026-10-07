package scheduler

import "testing"

func TestSnapshot(t *testing.T) { s:=Snapshot{Pending:2}; if s.Pending!=2 { t.Fatal("bad snapshot") } }
