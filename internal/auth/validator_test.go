package auth

import "testing"

func TestValidToken(t *testing.T) { if !Valid(Token{Value:"x",Subject:"user"}) { t.Fatal("token should be valid") } }
