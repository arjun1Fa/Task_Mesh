package config

func (c Config) Valid() bool {
	return c.DataFile != "" &&
		c.HTTPAddr != "" &&
		c.WorkerCount > 0 &&
		c.RetryAttempts > 0 &&
		c.RetryBaseDelay > 0 &&
		c.SchedulerPoll > 0 &&
		c.TaskTimeout > 0 &&
		c.AutoscaleMin > 0 &&
		c.AutoscaleMax >= c.AutoscaleMin &&
		c.AutoscaleHigh > 0 &&
		c.AutoscaleLow >= 0 &&
		c.AutoscalePoll > 0
}
