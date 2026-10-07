package retry

import ("testing"; "time")

func TestJitter(t *testing.T) {
  if WithJitter(time.Second,500*time.Millisecond) != 1500*time.Millisecond { t.Fatal("bad jitter") }
}
