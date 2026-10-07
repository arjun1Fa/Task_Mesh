package observability

import "sync/atomic"

type Gauge struct { n atomic.Int64 }
func (g *Gauge) Set(v int64) { g.n.Store(v) }
func (g *Gauge) Value() int64 { return g.n.Load() }
