package dlq

import ("testing"; "taskmesh/internal/core")

func TestQueueStoresFailedTasks(t *testing.T) {
  q:=NewQueue(); q.AddTask(core.Task{ID:"failed"},3,"attempts exhausted")
  items:=q.List()
  if len(items)!=1 || items[0].Task.ID!="failed" || items[0].Attempts!=3 { t.Fatal("dead letter item missing") }
}
