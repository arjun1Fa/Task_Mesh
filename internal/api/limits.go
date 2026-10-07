package api

import "net/http"

func withBodyLimit(next http.Handler) http.Handler { return http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){ r.Body=http.MaxBytesReader(w,r.Body,1<<20); next.ServeHTTP(w,r) }) }
