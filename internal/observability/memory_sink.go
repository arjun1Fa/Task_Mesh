package observability

type MemorySink struct { Events []Event }
func (s *MemorySink) Emit(e Event) { s.Events=append(s.Events,e) }
