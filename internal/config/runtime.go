package config

func Resolve() Config {
	c := Defaults()
	c.DataFile = Env("TASKMESH_DATA_FILE", c.DataFile)
	c.HTTPAddr = Env("TASKMESH_ADDR", c.HTTPAddr)
	c.WorkerCount = EnvInt("TASKMESH_WORKERS", c.WorkerCount)
	c.RetryAttempts = EnvInt("TASKMESH_RETRY_ATTEMPTS", c.RetryAttempts)
	c.RetryBaseDelay = EnvDuration("TASKMESH_RETRY_BASE_DELAY", c.RetryBaseDelay)
	c.SchedulerPoll = EnvDuration("TASKMESH_SCHEDULER_POLL", c.SchedulerPoll)
	c.TaskTimeout = EnvDuration("TASKMESH_TASK_TIMEOUT", c.TaskTimeout)
	c.AutoscaleEnabled = EnvBool("TASKMESH_AUTOSCALE_ENABLED", c.AutoscaleEnabled)
	c.AutoscaleMin = EnvInt("TASKMESH_AUTOSCALE_MIN", c.AutoscaleMin)
	c.AutoscaleMax = EnvInt("TASKMESH_AUTOSCALE_MAX", c.AutoscaleMax)
	c.AutoscaleHigh = EnvInt("TASKMESH_AUTOSCALE_HIGH", c.AutoscaleHigh)
	c.AutoscaleLow = EnvInt("TASKMESH_AUTOSCALE_LOW", c.AutoscaleLow)
	c.AutoscalePoll = EnvDuration("TASKMESH_AUTOSCALE_POLL", c.AutoscalePoll)
	return c
}
