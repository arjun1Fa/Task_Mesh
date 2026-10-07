package idempotency

import "testing"

func TestStore(t *testing.T) {
  s:=NewStore(); s.Record("req-1","task-1")
  got,ok:=s.Seen("req-1")
  if !ok || got!="task-1" { t.Fatal("idempotency record missing") }
}
