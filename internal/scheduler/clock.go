package scheduler

import "time"

type Clock func() time.Time
func RealClock() time.Time { return time.Now().UTC() }
