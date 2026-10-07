package auth

func Valid(t Token) bool { return t.Value!="" && t.Subject!="" }
