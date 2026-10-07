package observability

import "testing"

func TestRegistry(t *testing.T) { r:=NewRegistry(); if r==nil || r.Counters==nil { t.Fatal("registry missing") } }
