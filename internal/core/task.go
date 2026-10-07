package core

import "time"

// Task is the durable description of one unit of work.
//
// ID is the stable identity of the task. RunID is the identity of the
// current execution attempt and is regenerated when a recurring task fires.
// Status describes the lifecycle state visible to clients.
type Task struct {
	ID          string
	RunID       string
	Name        string
	Payload     []byte
	CreatedAt   time.Time
	Status      Status
	ScheduledAt *time.Time
	RepeatEvery time.Duration
	MaxAttempts int
	Timeout     time.Duration
	Priority    int
	Metadata    map[string]string
}

// Clone returns a defensive copy so callers cannot mutate runtime-owned
// payload or metadata after a task is queued.
func (t Task) Clone() Task {
	out := t
	out.Payload = append([]byte(nil), t.Payload...)
	if t.Metadata != nil {
		out.Metadata = make(map[string]string, len(t.Metadata))
		for k, v := range t.Metadata {
			out.Metadata[k] = v
		}
	}
	if t.ScheduledAt != nil {
		s := *t.ScheduledAt
		out.ScheduledAt = &s
	}
	return out
}
