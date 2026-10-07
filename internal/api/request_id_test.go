package api

import "testing"

func TestRequestID(t *testing.T) { if requestID()=="" { t.Fatal("request id missing") } }
