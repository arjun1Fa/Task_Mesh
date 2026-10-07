package benchmarks

import ("testing"; "taskmesh/internal/core"; "taskmesh/internal/queue")

func BenchmarkFIFOEnqueue(b *testing.B) { q:=queue.NewFIFO(); t:=core.Task{ID:"bench",Name:"benchmark"}; for i:=0;i<b.N;i++{ _=q.Enqueue(t); _,_=q.Dequeue() } }
