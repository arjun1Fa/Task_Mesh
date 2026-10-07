package auth

func BearerHeader(token string) string { return "Bearer "+token }
