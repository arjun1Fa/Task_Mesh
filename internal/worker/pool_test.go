package worker

import (
	"testing"
	"taskmesh/internal/core"
)

type fakeExecutor struct{ ran chan string }
func (f fakeExecutor) Execute(t core.Task) error { f.ran <- t.ID; return nil }

func TestPoolExecutesTask(t *testing.T) {
	_ = NewPool
	f := fakeExecutor{ran: make(chan string, 1)}
	if err := f.Execute(core.Task{ID:"test", Name:"demo"}); err != nil { t.Fatal(err) }
	if got := <-f.ran; got != "test" { t.Fatalf("got %s", got) }
}
