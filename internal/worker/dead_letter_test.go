package worker

import ("testing"; "taskmesh/internal/core"; "taskmesh/internal/dlq")

func TestSendToDLQ(t *testing.T) { q:=dlq.NewQueue(); SendToDLQ(q,core.Task{ID:"x"},4,"failed"); if q.Len()!=1 { t.Fatal("task not sent to dlq") } }
