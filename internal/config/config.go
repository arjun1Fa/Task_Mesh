package config

import "time"

type Config struct {
	DataFile          string
	HTTPAddr         string
	WorkerCount      int
	RetryAttempts    int
	RetryBaseDelay   time.Duration
	SchedulerPoll    time.Duration
	TaskTimeout      time.Duration
	AutoscaleEnabled bool
	AutoscaleMin     int
	AutoscaleMax     int
	AutoscaleHigh    int
	AutoscaleLow     int
	AutoscalePoll    time.Duration
}
