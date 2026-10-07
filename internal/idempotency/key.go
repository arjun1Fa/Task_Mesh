package idempotency

type Key string

func (k Key) Valid() bool { return k != "" }
