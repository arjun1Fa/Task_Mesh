package queue

import (
	"testing"
	"taskmesh/internal/core"
)

func TestFIFOOrder(t *testing.T) {
	q := NewFIFO()
	_ = q.Enqueue(core.Task{ID:"1", Name:"one"})
	_ = q.Enqueue(core.Task{ID:"2", Name:"two"})
	first, _ := q.Dequeue()
	second, _ := q.Dequeue()
	if first.ID != "1" || second.ID != "2" { t.Fatalf("unexpected order") }
}

func TestFIFOEmpty(t *testing.T) {
	q := NewFIFO()
	if _, ok := q.Dequeue(); ok { t.Fatal("expected empty queue") }
}
