package scheduler

import "time"

func ValidTime(t time.Time) bool { return !t.IsZero() }
