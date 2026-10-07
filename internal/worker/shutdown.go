package worker

import "context"

func Shutdown(ctx context.Context) error { return ctx.Err() }
