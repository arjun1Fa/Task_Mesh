package dlq

import "taskmesh/internal/core"

type Item struct { Task core.Task; Attempts int; Reason string }
