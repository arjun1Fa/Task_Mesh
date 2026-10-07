package api

import "net/http"

func cancelHandler(w http.ResponseWriter,_ *http.Request) { writeJSON(w,http.StatusAccepted,map[string]string{"status":"cancellation-requested"}) }
