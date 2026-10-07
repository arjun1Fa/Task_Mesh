package observability

import "testing"

func TestHealth(t *testing.T) { if !(Health{Liveness:true,Readiness:true}).OK() { t.Fatal("health should be ok") } }
