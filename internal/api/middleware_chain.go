package api

import "net/http"

func chain(h http.Handler) http.Handler { return withRequestID(withBodyLimit(h)) }
