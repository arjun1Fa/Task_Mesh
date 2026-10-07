package auth

import "net/http"

func Middleware(next http.Handler, check func(string) bool) http.Handler {
 return http.HandlerFunc(func(w http.ResponseWriter,r *http.Request) {
  if !check(r.Header.Get("Authorization")) { http.Error(w,"unauthorized",http.StatusUnauthorized); return }
  next.ServeHTTP(w,r)
 })
}
