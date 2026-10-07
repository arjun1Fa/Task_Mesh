package core

type Cancellation struct { Requested bool; Reason string }

func (c Cancellation) Active() bool { return c.Requested }
