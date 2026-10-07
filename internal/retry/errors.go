package retry

import "errors"

var ErrAttemptsExhausted = errors.New("retry attempts exhausted")
