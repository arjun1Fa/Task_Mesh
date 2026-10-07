package scheduler

import "taskmesh/internal/core"

// Item is one scheduled occurrence. RepeatEvery of zero means one-shot.
type Item struct {
	Task        core.Task
	RunAtUnix   int64 // nanoseconds since Unix epoch
	RepeatEvery int64 // nanoseconds; zero means one-shot
}
