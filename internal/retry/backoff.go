package retry

import "time"

func Delay(base time.Duration, attempt int) time.Duration {
  if attempt < 1 { attempt = 1 }
  out := base
  for i:=1; i<attempt; i++ { out *= 2 }
  return out
}
