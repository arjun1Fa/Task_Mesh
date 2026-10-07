package core

import (
	"errors"
	"time"
)

var (
	ErrTaskIDRequired      = errors.New("task id is required")
	ErrTaskNameRequired    = errors.New("task name is required")
	ErrTaskAttemptsInvalid = errors.New("max attempts must be greater than zero")
	ErrTaskTimeoutInvalid  = errors.New("timeout cannot be negative")
	ErrTaskRepeatInvalid   = errors.New("repeat interval cannot be negative")
	ErrTaskScheduleInvalid = errors.New("scheduled time cannot be zero")
)

// Validate checks a task that already has its stable identity.
func (t Task) Validate() error {
	if t.ID == "" {
		return ErrTaskIDRequired
	}
	return t.ValidateDefinition()
}

// ValidateDefinition checks task fields that are independent of the generated
// stable ID. API transports use this before Runtime.Submit assigns an ID.
func (t Task) ValidateDefinition() error {
	if t.Name == "" {
		return ErrTaskNameRequired
	}
	if t.MaxAttempts < 0 {
		return ErrTaskAttemptsInvalid
	}
	if t.Timeout < 0 {
		return ErrTaskTimeoutInvalid
	}
	if t.RepeatEvery < 0 {
		return ErrTaskRepeatInvalid
	}
	if t.ScheduledAt != nil && t.ScheduledAt.IsZero() {
		return ErrTaskScheduleInvalid
	}
	if t.RepeatEvery > 0 && t.ScheduledAt == nil {
		return errors.New("recurring tasks require scheduled time")
	}
	return nil
}

func (t Task) Normalized(now time.Time) Task {
	out := t.Clone()
	if out.CreatedAt.IsZero() {
		out.CreatedAt = now.UTC()
	}
	if out.Status == "" {
		out.Status = StatusQueued
	}
	if out.MaxAttempts == 0 {
		out.MaxAttempts = 1
	}
	return out
}
