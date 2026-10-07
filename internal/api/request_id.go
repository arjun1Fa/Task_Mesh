package api

import ("crypto/rand"; "encoding/hex"; "net/http")

func requestID() string { b:=make([]byte,8); if _,err:=rand.Read(b); err!=nil { return "unknown" }; return hex.EncodeToString(b) }
func withRequestID(next http.Handler) http.Handler { return http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){ w.Header().Set("X-Request-ID",requestID()); next.ServeHTTP(w,r) }) }
