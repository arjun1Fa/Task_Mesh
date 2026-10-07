package observability

type Registry struct { Counters map[string]*Counter; Gauges map[string]*Gauge }
func NewRegistry() *Registry { return &Registry{Counters:map[string]*Counter{},Gauges:map[string]*Gauge{}} }
