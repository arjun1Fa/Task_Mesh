package retry

import "time"

func WithJitter(delay time.Duration, extra time.Duration) time.Duration { return delay + extra }
