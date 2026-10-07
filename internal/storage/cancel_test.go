package storage

import "testing"

func TestCancelStatus(t *testing.T) { if CancelStatus=="" { t.Fatal("missing status") } }
