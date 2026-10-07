package observability

import "testing"

func TestMemorySink(t *testing.T) { s:=&MemorySink{}; s.Emit(Event{Name:"queued"}); if len(s.Events)!=1 { t.Fatal("event missing") } }
