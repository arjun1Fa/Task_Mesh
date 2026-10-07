package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"taskmesh/internal/api"
	"taskmesh/internal/config"
	"taskmesh/internal/core"
	"taskmesh/internal/queue"
	taskruntime "taskmesh/internal/runtime"
	"taskmesh/internal/retry"
	"taskmesh/internal/storage"
	"taskmesh/internal/worker"
)

func main() {
	cfg := config.Resolve()
	if !cfg.Valid() {
		log.Fatal("invalid TaskMesh configuration")
	}

	repo, err := storage.NewFileRepository(cfg.DataFile)
	if err != nil {
		log.Fatalf("open task data: %v", err)
	}
	q := queue.NewPriorityQueue()
	registry := worker.NewRegistry()

	// "log" is a deliberately small example handler. Real deployments
	// register application-specific executors during bootstrap.
	registry.MustRegister("log", worker.ExecutorFunc(func(t core.Task) error {
		log.Printf("taskmesh task=%s run=%s payload=%s", t.ID, t.RunID, string(t.Payload))
		return nil
	}))

	rt := taskruntime.New(repo, q, registry, taskruntime.Config{
		WorkerCount:     cfg.WorkerCount,
		SchedulerPoll:   cfg.SchedulerPoll,
		TaskTimeout:     cfg.TaskTimeout,
		ResultHistoryMax: 1000,
		Retry: retry.Policy{
			MaxAttempts: cfg.RetryAttempts,
			BaseDelay:   cfg.RetryBaseDelay,
		},
		AutoScale: taskruntime.AutoScaleConfig{
			Enabled:       cfg.AutoscaleEnabled,
			MinWorkers:    cfg.AutoscaleMin,
			MaxWorkers:    cfg.AutoscaleMax,
			HighWatermark: cfg.AutoscaleHigh,
			LowWatermark:  cfg.AutoscaleLow,
			PollInterval:  cfg.AutoscalePoll,
		},
	})

	ctx, stopSignals := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stopSignals()

	if err := rt.Start(ctx); err != nil {
		log.Fatal(err)
	}

	server := &http.Server{
		Addr:              cfg.HTTPAddr,
		Handler:           api.NewRuntimeServer(rt).Handler(),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	go func() {
		log.Printf("taskmesh listening on %s", cfg.HTTPAddr)
		if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Printf("server error: %v", err)
			stopSignals()
		}
	}()

	<-ctx.Done()

	rt.Stop()
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Printf("shutdown error: %v", err)
	}
}
