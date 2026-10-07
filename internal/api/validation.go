package api

import ("net/http"; "strings")

func pathID(r *http.Request) string { return strings.TrimSpace(r.URL.Query().Get("id")) }
