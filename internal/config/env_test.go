package config

import "testing"

func TestEnvFallback(t *testing.T) { if Env("TASKMESH_MISSING","x")!="x"{t.Fatal("fallback mismatch")} }
