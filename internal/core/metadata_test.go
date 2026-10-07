package core

import "testing"

func TestMetadata(t *testing.T) { m:=Metadata{CorrelationID:"c1"}; if m.CorrelationID!="c1"{t.Fatal("metadata mismatch")} }
