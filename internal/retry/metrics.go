package retry

import "sync/atomic"

type Metrics struct { attempts atomic.Int64; failures atomic.Int64 }

func (m *Metrics) Attempt() { m.attempts.Add(1) }
func (m *Metrics) Failure() { m.failures.Add(1) }
func (m *Metrics) Attempts() int64 { return m.attempts.Load() }
func (m *Metrics) Failures() int64 { return m.failures.Load() }
