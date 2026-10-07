package api

import "net/http"

func supportsMethod(r *http.Request, method string) bool { return r.Method==method }
