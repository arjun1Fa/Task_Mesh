package config

import "time"

func Defaults() Config {
	return Config{
		DataFile:          "taskmesh-data.json",
		HTTPAddr:         ":8080",
		WorkerCount:      4,
		RetryAttempts:    3,
		RetryBaseDelay:   time.Second,
		SchedulerPoll:    250 * time.Millisecond,
		TaskTimeout:      30 * time.Second,
		AutoscaleEnabled: false,
		AutoscaleMin:     1,
		AutoscaleMax:     8,
		AutoscaleHigh:    8,
		AutoscaleLow:     0,
		AutoscalePoll:    time.Second,
	}
}
