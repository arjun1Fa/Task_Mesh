package retry

import "time"

type Policy struct { MaxAttempts int; BaseDelay time.Duration }

func (p Policy) Attempts() int {
  if p.MaxAttempts < 1 { return 1 }
  return p.MaxAttempts
}
