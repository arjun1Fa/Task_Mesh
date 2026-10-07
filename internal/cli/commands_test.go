package cli

import "testing"

func TestCommandNames(t *testing.T) { if CommandEnqueue==CommandGet { t.Fatal("duplicate command") } }
