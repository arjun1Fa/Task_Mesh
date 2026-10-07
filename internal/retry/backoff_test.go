package retry

import ("testing"; "time")

func TestDelay(t *testing.T) {
  if Delay(time.Second,3) != 4*time.Second { t.Fatal("unexpected delay") }
}
