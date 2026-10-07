package scheduler

import (
	"context"
	"errors"
	"taskmesh/internal/core"
	"time"
)

func Run(ctx context.Context, s *Scheduler, interval time.Duration, emit func(core.Task)) error {
	if interval <= 0 {
		return ErrInvalidInterval
	}
	if emit == nil {
		return errors.New("scheduler emit callback is required")
	}
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			for _, t := range s.Due() {
				emit(t)
			}
		}
	}
}
