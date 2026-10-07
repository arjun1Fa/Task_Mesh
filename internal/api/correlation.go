package api

import "net/http"

func correlationID(r *http.Request) string { return r.Header.Get("X-Correlation-ID") }
