package retry

import "testing"

func TestMetrics(t *testing.T) {
  var m Metrics; m.Attempt(); m.Failure()
  if m.Attempts()!=1 || m.Failures()!=1 { t.Fatal("metrics mismatch") }
}
