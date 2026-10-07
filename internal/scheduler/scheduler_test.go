package scheduler

import (
	"testing"
	"taskmesh/internal/core"
	"time"
)

func TestDue(t *testing.T) {
	now := time.Date(2026, 1, 1, 12, 0, 0, 0, time.UTC)
	s := New(func() time.Time { return now })
	s.Schedule(core.Task{ID: "a", Name: "a"}, now.Add(-time.Second))
	s.Schedule(core.Task{ID: "b", Name: "b"}, now.Add(time.Hour))
	got := s.Due()
	if len(got) != 1 || got[0].ID != "a" {
		t.Fatal("unexpected due tasks")
	}
}

func TestRecurringTaskRemainsScheduled(t *testing.T) {
	now := time.Date(2026, 1, 1, 12, 0, 0, 0, time.UTC)
	s := New(func() time.Time { return now })
	repeat := time.Second
	s.Schedule(core.Task{ID: "repeat", Name: "repeat", RepeatEvery: repeat}, now.Add(-time.Millisecond))
	got := s.Due()
	if len(got) != 1 {
		t.Fatalf("got %d due tasks", len(got))
	}
	if s.Len() != 1 {
		t.Fatal("recurring item was removed")
	}
	pending := s.Pending()
	if !pending[0].Task.ScheduledAt.After(now) {
		t.Fatal("next occurrence was not moved into the future")
	}
}

func TestRescheduleAndCancel(t *testing.T) {
	now := time.Date(2026, 1, 1, 12, 0, 0, 0, time.UTC)
	s := New(func() time.Time { return now })
	s.Schedule(core.Task{ID: "move", Name: "move"}, now.Add(time.Hour))
	next := now.Add(2 * time.Hour)
	if err := s.Reschedule("move", next); err != nil {
		t.Fatal(err)
	}
	if !s.Cancel("move") {
		t.Fatal("expected task cancellation")
	}
	if s.Len() != 0 {
		t.Fatal("canceled schedule remains pending")
	}
}
