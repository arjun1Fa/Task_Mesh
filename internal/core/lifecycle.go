package core

func Terminal(s Status) bool { return s==StatusSucceeded || s==StatusFailed }
