package core

import "testing"

func TestTerminalStates(t *testing.T) { if !Terminal(StatusSucceeded) || !Terminal(StatusFailed) { t.Fatal("terminal state missing") } }
