package api

import "net/http"

func idempotencyHeader(r *http.Request) string { return r.Header.Get("Idempotency-Key") }
