package worker

import "time"

type Clock func() time.Time

func now() time.Time { return time.Now().UTC() }
