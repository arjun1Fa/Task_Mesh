package config

import "testing"

func TestDefaultsValid(t *testing.T) { if !Defaults().Valid(){t.Fatal("defaults invalid")} }
