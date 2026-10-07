package worker

import ("taskmesh/internal/core"; "taskmesh/internal/dlq")

func SendToDLQ(q *dlq.Queue, task core.Task, attempts int, reason string) { q.AddTask(task,attempts,reason) }
