package dlq

import "taskmesh/internal/core"

func Recover(i Item) core.Task { return i.Task }
