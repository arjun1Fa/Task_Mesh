package observability

type Health struct { Liveness bool; Readiness bool }
func (h Health) OK() bool { return h.Liveness && h.Readiness }
