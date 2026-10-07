package worker

import "context"

func Canceled(ctx context.Context) bool { select { case <-ctx.Done(): return true; default: return false } }
