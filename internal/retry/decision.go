package retry

func ShouldRetry(attempt,max int) bool { return attempt < max }
