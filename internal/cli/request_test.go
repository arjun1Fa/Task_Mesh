package cli

import "testing"

func TestRequest(t *testing.T) { r:=Request{Method:"GET",Path:"/tasks"}; if r.Method!="GET" { t.Fatal("request mismatch") } }
