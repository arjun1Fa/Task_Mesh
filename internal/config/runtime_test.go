package config

import "testing"

func TestResolve(t *testing.T) { if !Resolve().Valid(){t.Fatal("resolved config invalid")} }
