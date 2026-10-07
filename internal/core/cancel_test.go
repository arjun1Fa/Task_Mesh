package core

import "testing"

func TestCancellation(t *testing.T) { if !(Cancellation{Requested:true}).Active() { t.Fatal("cancellation not active") } }
