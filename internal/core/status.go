package core

// Status represents the lifecycle of a task.
type Status string

const (
	StatusQueued     Status = "queued"
	StatusScheduled  Status = "scheduled"
	StatusRunning    Status = "running"
	StatusRetrying   Status = "retrying"
	StatusSucceeded  Status = "succeeded"
	StatusFailed     Status = "failed"
	StatusCanceled   Status = "canceled"
	StatusDeadLetter Status = "dead_letter"
)

// Terminal reports whether a task has reached a state that does not require
// another automatic execution.
func Terminal(s Status) bool {
	return s == StatusSucceeded || s == StatusFailed ||
		s == StatusCanceled || s == StatusDeadLetter
}
