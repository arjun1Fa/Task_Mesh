package core

import "time"

// TaskResult captures the outcome of one execution run.
type TaskResult struct {
	TaskID     string
	RunID      string
	Attempt    int
	StartedAt  time.Time
	FinishedAt time.Time
	Status     Status
	Error      string
}

// Succeeded reports whether the execution completed successfully.
func (r TaskResult) Succeeded() bool { return r.Status == StatusSucceeded }
