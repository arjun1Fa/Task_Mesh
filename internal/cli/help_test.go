package cli

import "testing"

func TestHelp(t *testing.T) { if Help()=="" { t.Fatal("help missing") } }
