package scheduler

import (
	"errors"
	"sort"
	"sync"
	"taskmesh/internal/core"
	"time"
)

var (
	ErrAlreadyScheduled = errors.New("task is already scheduled")
	ErrNotScheduled     = errors.New("task is not scheduled")
	ErrInvalidInterval  = errors.New("scheduler interval must be positive")
)

// Scheduler is a thread-safe in-memory scheduler for delayed and recurring
// tasks. Scheduled tasks are ordered by next run time.
type Scheduler struct {
	mu        sync.Mutex
	items     []Item
	maxItems  int
	now       Clock
}

func New(c Clock) *Scheduler {
	if c == nil {
		c = RealClock
	}
	return &Scheduler{now: c}
}

func NewWithLimit(c Clock, maxItems int) *Scheduler {
	s := New(c)
	s.maxItems = maxItems
	return s
}

func (s *Scheduler) Schedule(t core.Task, at time.Time) error {
	if err := t.Validate(); err != nil {
		return err
	}
	if at.IsZero() {
		return core.ErrTaskScheduleInvalid
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, item := range s.items {
		if item.Task.ID == t.ID {
			return ErrAlreadyScheduled
		}
	}
	if s.maxItems > 0 && len(s.items) >= s.maxItems {
		return ErrScheduleLimit
	}
	t.ScheduledAt = &at
	s.items = append(s.items, Item{Task: t.Clone(), RunAtUnix: at.UnixNano(), RepeatEvery: int64(t.RepeatEvery)})
	s.sortLocked()
	return nil
}

func (s *Scheduler) Reschedule(id string, at time.Time) error {
	if id == "" || at.IsZero() {
		return core.ErrTaskScheduleInvalid
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	for i := range s.items {
		if s.items[i].Task.ID == id {
			t := s.items[i].Task.Clone()
			t.ScheduledAt = &at
			s.items[i].Task = t
			s.items[i].RunAtUnix = at.UnixNano()
			s.sortLocked()
			return nil
		}
	}
	return ErrNotScheduled
}

func (s *Scheduler) Cancel(id string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	for i := range s.items {
		if s.items[i].Task.ID == id {
			s.items[i] = s.items[len(s.items)-1]
			s.items = s.items[:len(s.items)-1]
			s.sortLocked()
			return true
		}
	}
	return false
}

// Due returns tasks whose next run time has arrived. Recurring entries are
// retained and advanced to the next future occurrence.
func (s *Scheduler) Due() []core.Task {
	s.mu.Lock()
	defer s.mu.Unlock()

	now := s.now().UnixNano()
	var out []core.Task
	remaining := s.items[:0]

	for _, item := range s.items {
		if item.RunAtUnix > now {
			remaining = append(remaining, item)
			continue
		}

		t := item.Task.Clone()
		runAt := time.Unix(0, item.RunAtUnix).UTC()
		t.ScheduledAt = &runAt
		out = append(out, t)

		if item.RepeatEvery > 0 {
			next := now + item.RepeatEvery
			item.RunAtUnix = next
			nextTime := time.Unix(0, next).UTC()
			item.Task.ScheduledAt = &nextTime
			remaining = append(remaining, item)
		}
	}

	s.items = remaining
	s.sortLocked()
	return out
}

func (s *Scheduler) Pending() []Item {
	s.mu.Lock()
	defer s.mu.Unlock()
	out := make([]Item, len(s.items))
	copy(out, s.items)
	for i := range out {
		out[i].Task = out[i].Task.Clone()
	}
	return out
}

func (s *Scheduler) Len() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.items)
}

func (s *Scheduler) sortLocked() {
	sort.Slice(s.items, func(i, j int) bool {
		return s.items[i].RunAtUnix < s.items[j].RunAtUnix
	})
}
