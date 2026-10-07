package observability

import "log"

func LogEvent(e Event) { log.Printf("event=%s task=%s %s",e.Name,e.TaskID,e.Message) }
