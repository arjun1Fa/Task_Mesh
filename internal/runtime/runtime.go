package runtime

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"sync/atomic"
	"time"

	"taskmesh/internal/core"
	"taskmesh/internal/dlq"
	"taskmesh/internal/idempotency"
	"taskmesh/internal/observability"
	"taskmesh/internal/queue"
	"taskmesh/internal/retry"
	"taskmesh/internal/scheduler"
	"taskmesh/internal/storage"
	"taskmesh/internal/worker"
)

var (
	ErrRuntimeStopped   = errors.New("taskmesh runtime is stopped")
	ErrExecutorMissing  = errors.New("no executor registered for task")
	ErrTaskCanceled     = errors.New("task was canceled")
	ErrAlreadyCompleted = errors.New("task is already terminal")
)

type Config struct {
	WorkerCount      int
	SchedulerPoll    time.Duration
	Retry            retry.Policy
	TaskTimeout      time.Duration
	AutoScale        AutoScaleConfig
	ResultHistoryMax int
}

type AutoScaleConfig struct {
	Enabled       bool
	MinWorkers    int
	MaxWorkers    int
	HighWatermark int
	LowWatermark  int
	PollInterval  time.Duration
}

// Runtime connects scheduling, persistence, queueing, workers, retries,
// cancellation, idempotency, the dead-letter queue and observability into
// one lifecycle-managed execution engine.
type Runtime struct {
	repo      storage.TaskRepository
	queue     queue.TaskQueue
	scheduler *scheduler.Scheduler
	registry  *worker.Registry
	dlq       *dlq.Queue
	idem      *idempotency.Store
	events    *observability.Registry

	pool *worker.Pool
	cfg  Config

	mu      sync.RWMutex
	started bool
	stop    context.CancelFunc
	active  map[string]context.CancelFunc
	results map[string]core.TaskResult
	order   []string
	seq     atomic.Uint64
	metricMu sync.Mutex
}

func New(repo storage.TaskRepository, q queue.TaskQueue, reg *worker.Registry, cfg Config) *Runtime {
	if repo == nil {
		repo = storage.NewMemoryRepository()
	}
	if q == nil {
		q = queue.NewPriorityQueue()
	}
	if reg == nil {
		reg = worker.NewRegistry()
	}
	cfg = normalizeConfig(cfg)
	r := &Runtime{
		repo:      repo,
		queue:     q,
		scheduler: scheduler.New(nil),
		registry:  reg,
		dlq:       dlq.NewQueue(),
		idem:      idempotency.NewStore(),
		events:    observability.NewRegistry(),
		cfg:       cfg,
		active:    make(map[string]context.CancelFunc),
		results:   make(map[string]core.TaskResult),
	}
	r.pool = worker.NewPool(q, worker.ExecutorFunc(r.execute), cfg.WorkerCount)
	return r
}

func normalizeConfig(c Config) Config {
	if c.WorkerCount < 1 {
		c.WorkerCount = 1
	}
	if c.SchedulerPoll <= 0 {
		c.SchedulerPoll = 250 * time.Millisecond
	}
	if c.Retry.MaxAttempts < 1 {
		c.Retry.MaxAttempts = 1
	}
	if c.Retry.BaseDelay <= 0 {
		c.Retry.BaseDelay = 500 * time.Millisecond
	}
	if c.TaskTimeout <= 0 {
		c.TaskTimeout = 30 * time.Second
	}
	if c.ResultHistoryMax < 1 {
		c.ResultHistoryMax = 1000
	}
	if c.AutoScale.MinWorkers < 1 {
		c.AutoScale.MinWorkers = 1
	}
	if c.AutoScale.MaxWorkers < c.AutoScale.MinWorkers {
		c.AutoScale.MaxWorkers = c.WorkerCount
	}
	if c.AutoScale.MaxWorkers < c.AutoScale.MinWorkers {
		c.AutoScale.MaxWorkers = c.AutoScale.MinWorkers
	}
	if c.AutoScale.HighWatermark < 1 {
		c.AutoScale.HighWatermark = c.WorkerCount * 2
	}
	if c.AutoScale.LowWatermark < 0 {
		c.AutoScale.LowWatermark = 0
	}
	if c.AutoScale.PollInterval <= 0 {
		c.AutoScale.PollInterval = time.Second
	}
	return c
}

// Start launches scheduler, workers and optional autoscaling. Start is
// idempotent; the returned error only reports an invalid lifecycle request.
func (r *Runtime) Start(ctx context.Context) error {
	r.mu.Lock()
	if r.started {
		r.mu.Unlock()
		return nil
	}
	child, cancel := context.WithCancel(ctx)
	r.started = true
	r.stop = cancel
	r.mu.Unlock()

	r.rehydrate()

	go func() {
		_ = scheduler.Run(child, r.scheduler, r.cfg.SchedulerPoll, func(t core.Task) {
			r.enqueueScheduled(t)
		})
	}()
	go r.pool.Run(child)
	if r.cfg.AutoScale.Enabled {
		go r.autoscale(child)
	}
	return nil
}

func (r *Runtime) Stop() {
	r.mu.Lock()
	if !r.started {
		r.mu.Unlock()
		return
	}
	cancel := r.stop
	r.started = false
	r.stop = nil
	r.mu.Unlock()

	cancel()
	r.mu.Lock()
	for _, c := range r.active {
		c()
	}
	r.active = make(map[string]context.CancelFunc)
	r.mu.Unlock()
}

func (r *Runtime) Submit(ctx context.Context, t core.Task, idemKey string) (core.Task, bool, error) {
	if t.ID == "" {
		t.ID = r.newID()
	}
	if err := t.Validate(); err != nil {
		return core.Task{}, false, err
	}
	if !r.isStarted() {
		return core.Task{}, false, ErrRuntimeStopped
	}

	reservedKey := false
	if idemKey != "" {
		existingID, already := r.idem.Reserve(idempotency.Key(idemKey), t.ID)
		if already {
			existing, exists := r.repo.Get(existingID)
			if !exists {
				return core.Task{}, false, storage.ErrNotFound
			}
			return existing, true, nil
		}
		reservedKey = true
	}

	now := time.Now().UTC()
	t = t.Normalized(now)
	if t.ID == "" {
		t.ID = r.newID()
	}
	t.RunID = r.newRunID()
	if _, exists := r.repo.Get(t.ID); exists {
		if reservedKey {
			r.idem.Forget(idempotency.Key(idemKey))
		}
		return core.Task{}, false, storage.ErrAlreadyExists
	}
	if t.Timeout <= 0 {
		t.Timeout = r.cfg.TaskTimeout
	}
	if t.RepeatEvery > 0 && t.ScheduledAt == nil {
		if reservedKey {
			r.idem.Forget(idempotency.Key(idemKey))
		}
		return core.Task{}, false, errors.New("recurring tasks require scheduled_at")
	}
	if t.MaxAttempts <= 0 {
		t.MaxAttempts = r.cfg.Retry.MaxAttempts
	}

	if t.RepeatEvery > 0 {
		if t.ScheduledAt.Before(now) {
			at := now
			t.ScheduledAt = &at
		}
		t.Status = core.StatusScheduled
		if err := r.repo.Create(t); err != nil {
			if reservedKey { r.idem.Forget(idempotency.Key(idemKey)) }
			return core.Task{}, false, err
		}
		if err := r.scheduler.Schedule(t, *t.ScheduledAt); err != nil {
			_ = r.repo.Delete(t.ID)
			if reservedKey { r.idem.Forget(idempotency.Key(idemKey)) }
			return core.Task{}, false, err
		}
	} else if t.ScheduledAt != nil && t.ScheduledAt.After(now) {
		t.Status = core.StatusScheduled
		if err := r.repo.Create(t); err != nil {
			if reservedKey { r.idem.Forget(idempotency.Key(idemKey)) }
			return core.Task{}, false, err
		}
		if err := r.scheduler.Schedule(t, *t.ScheduledAt); err != nil {
			_ = r.repo.Delete(t.ID)
			if reservedKey { r.idem.Forget(idempotency.Key(idemKey)) }
			return core.Task{}, false, err
		}
	} else {
		t.ScheduledAt = nil
		t.Status = core.StatusQueued
		if err := r.repo.Create(t); err != nil {
			if reservedKey { r.idem.Forget(idempotency.Key(idemKey)) }
			return core.Task{}, false, err
		}
		if err := r.queue.Enqueue(t); err != nil {
			t.Status = core.StatusCanceled
			_ = r.repo.Update(t)
			if reservedKey { r.idem.Forget(idempotency.Key(idemKey)) }
			return core.Task{}, false, err
		}
	}
	if idemKey != "" && !reservedKey {
		r.idem.Record(idempotency.Key(idemKey), t.ID)
	}
	r.emit("task.submitted", t.ID, t.Name)
	return t, false, nil
}

func (r *Runtime) Get(id string) (core.Task, bool) { return r.repo.Get(id) }

func (r *Runtime) List() []core.Task { return r.repo.List() }

func (r *Runtime) Schedule(id string, at time.Time, repeat time.Duration) (core.Task, error) {
	t, ok := r.repo.Get(id)
	if !ok {
		return core.Task{}, storage.ErrNotFound
	}
	if core.Terminal(t.Status) {
		return t, ErrAlreadyCompleted
	}
	r.scheduler.Cancel(id)
	t.RepeatEvery = repeat
	t.ScheduledAt = &at
	t.Status = core.StatusScheduled
	if err := r.repo.Update(t); err != nil {
		return core.Task{}, err
	}
	if err := r.scheduler.Schedule(t, at); err != nil {
		return core.Task{}, err
	}
	r.emit("task.rescheduled", id, "schedule updated")
	return t, nil
}

func (r *Runtime) Reschedule(id string, at time.Time) (core.Task, error) {
	t, ok := r.repo.Get(id)
	if !ok {
		return core.Task{}, storage.ErrNotFound
	}
	if err := r.scheduler.Reschedule(id, at); err != nil {
		return t, err
	}
	t.ScheduledAt = &at
	t.Status = core.StatusScheduled
	if err := r.repo.Update(t); err != nil {
		return core.Task{}, err
	}
	r.emit("task.rescheduled", id, "next run changed")
	return t, nil
}

func (r *Runtime) Cancel(id, reason string) (core.Task, error) {
	t, ok := r.repo.Get(id)
	if !ok {
		return core.Task{}, storage.ErrNotFound
	}
	if core.Terminal(t.Status) {
		return t, nil
	}
	r.scheduler.Cancel(id)
	if t.RunID != "" {
		r.mu.RLock()
		cancel := r.active[t.RunID]
		r.mu.RUnlock()
		if cancel != nil {
			cancel()
		}
	}
	t.Status = core.StatusCanceled
	if err := r.repo.Update(t); err != nil {
		return core.Task{}, err
	}
	r.emit("task.canceled", id, reason)
	return t, nil
}

func (r *Runtime) PendingSchedules() []scheduler.Item { return r.scheduler.Pending() }

func (r *Runtime) WorkerCount() int { return r.pool.Size() }

func (r *Runtime) QueueDepth() int { return r.queue.Len() }

func (r *Runtime) Metrics() map[string]int {
	return map[string]int{
		"workers": r.WorkerCount(),
		"queue_depth": r.QueueDepth(),
		"scheduled": r.scheduler.Len(),
		"dead_letter": r.dlq.Len(),
	}
}

func (r *Runtime) rehydrate() {
	for _, t := range r.repo.List() {
		switch t.Status {
		case core.StatusScheduled:
			if t.ScheduledAt != nil {
				if err := r.scheduler.Schedule(t, *t.ScheduledAt); err != nil {
					// A stale duplicate can only occur when Start is called more
					// than once; normal startup has an empty scheduler.
					continue
				}
			}
		case core.StatusQueued, core.StatusRunning, core.StatusRetrying:
			t.RunID = r.newRunID()
			t.Status = core.StatusQueued
			if err := r.repo.Update(t); err == nil {
				_ = r.queue.Enqueue(t)
			}
		}
	}
}

func (r *Runtime) ScaleWorkers(n int) {
	r.pool.Resize(n)
	r.emit("workers.resized", "", fmt.Sprintf("workers=%d", n))
}

func (r *Runtime) DLQ() []dlq.Item { return r.dlq.List() }

func (r *Runtime) RecoverDLQ(item dlq.Item) error {
	t := dlq.Recover(item)
	if t.ID == "" {
		return errors.New("dead-letter item has no task id")
	}
	t.Status = core.StatusQueued
	t.RunID = r.newRunID()
	if err := r.repo.Save(t); err != nil {
		return err
	}
	return r.queue.Enqueue(t)
}

func (r *Runtime) Result(runID string) (core.TaskResult, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	res, ok := r.results[runID]
	return res, ok
}

func (r *Runtime) execute(t core.Task) error {
	if r.isCanceled(t.ID) {
		return ErrTaskCanceled
	}
	handler, ok := r.registry.Get(t.Name)
	if !ok {
		return ErrExecutorMissing
	}

	ctx := context.Background()
	cancel := func() {}
	if t.Timeout > 0 {
		ctx, cancel = context.WithTimeout(ctx, t.Timeout)
	}
	r.mu.Lock()
	r.active[t.RunID] = cancel
	r.mu.Unlock()
	defer func() {
		cancel()
		r.mu.Lock()
		delete(r.active, t.RunID)
		r.mu.Unlock()
	}()

	started := time.Now().UTC()
	policy := retry.Policy{MaxAttempts: t.MaxAttempts, BaseDelay: r.cfg.Retry.BaseDelay}
	if policy.MaxAttempts < 1 {
		policy.MaxAttempts = 1
	}
	var lastErr error
	lastAttempt := 0
	for attempt := 1; attempt <= policy.Attempts(); attempt++ {
		lastAttempt = attempt
		if ctx.Err() != nil {
			lastErr = ctx.Err()
			break
		}
		if r.isCanceled(t.ID) {
			lastErr = ErrTaskCanceled
			break
		}
		t.Status = core.StatusRunning
		if err := r.repo.Update(t); err != nil {
			return err
		}
		var err error
		if contextHandler, ok := handler.(worker.ContextExecutor); ok {
			err = contextHandler.ExecuteContext(ctx, t)
		} else {
			err = handler.Execute(t)
		}
		if err == nil {
			if r.isCanceled(t.ID) {
				r.finish(t, attempt, started, core.StatusCanceled, ErrTaskCanceled.Error())
				return ErrTaskCanceled
			}
			r.finish(t, attempt, started, core.StatusSucceeded, "")
			return nil
		}
		lastErr = err
		if attempt < policy.Attempts() {
			t.Status = core.StatusRetrying
			_ = r.repo.Update(t)
			r.emit("task.retrying", t.ID, fmt.Sprintf("attempt=%d error=%s", attempt, err))
			wait := retry.Delay(policy.BaseDelay, attempt)
			timer := time.NewTimer(wait)
			select {
			case <-ctx.Done():
				timer.Stop()
				lastErr = ctx.Err()
			case <-timer.C:
			}
			if errors.Is(lastErr, ctx.Err()) {
				break
			}
		}
	}

	if errors.Is(lastErr, ErrTaskCanceled) || errors.Is(lastErr, context.Canceled) {
		t.Status = core.StatusCanceled
		_ = r.repo.Update(t)
		r.finish(t, lastAttempt, started, core.StatusCanceled, lastErr.Error())
		return lastErr
	}

	if t.RepeatEvery > 0 {
		t.Status = core.StatusScheduled
		if next, ok := r.nextScheduledTime(t.ID); ok {
			t.ScheduledAt = &next
		}
		_ = r.repo.Update(t)
		r.dlq.AddTask(t, lastAttempt, lastErr.Error())
		r.finish(t, lastAttempt, started, core.StatusDeadLetter, lastErr.Error())
		r.emit("task.dead_lettered", t.ID, lastErr.Error())
		return lastErr
	}
	t.Status = core.StatusDeadLetter
	_ = r.repo.Update(t)
	r.dlq.AddTask(t, lastAttempt, lastErr.Error())
	r.finish(t, lastAttempt, started, core.StatusDeadLetter, lastErr.Error())
	r.emit("task.dead_lettered", t.ID, lastErr.Error())
	return lastErr
}

func (r *Runtime) finish(t core.Task, attempt int, started time.Time, status core.Status, errText string) {
	persistedStatus := status
	if t.RepeatEvery > 0 && (status == core.StatusSucceeded || status == core.StatusDeadLetter) {
		persistedStatus = core.StatusScheduled
		if next, ok := r.nextScheduledTime(t.ID); ok {
			t.ScheduledAt = &next
		}
	}
	t.Status = persistedStatus
	_ = r.repo.Update(t)
	result := core.TaskResult{
		TaskID: t.ID, RunID: t.RunID, Attempt: attempt,
		StartedAt: started, FinishedAt: time.Now().UTC(),
		Status: status, Error: errText,
	}
	r.mu.Lock()
	r.results[result.RunID] = result
	r.order = append(r.order, result.RunID)
	for len(r.order) > r.cfg.ResultHistoryMax {
		delete(r.results, r.order[0])
		r.order = r.order[1:]
	}
	r.mu.Unlock()
	r.emit("task."+string(status), t.ID, errText)
}

func (r *Runtime) enqueueScheduled(t core.Task) {
	if r.isCanceled(t.ID) {
		return
	}
	t.RunID = r.newRunID()
	t.Status = core.StatusQueued
	if err := r.repo.Update(t); err != nil {
		return
	}
	_ = r.queue.Enqueue(t)
	r.emit("task.scheduled_due", t.ID, "")
}

func (r *Runtime) autoscale(ctx context.Context) {
	ticker := time.NewTicker(r.cfg.AutoScale.PollInterval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			depth := r.queue.Len()
			size := r.pool.Size()
			if depth >= r.cfg.AutoScale.HighWatermark && size < r.cfg.AutoScale.MaxWorkers {
				r.pool.Resize(size + 1)
				r.emit("workers.autoscaled", "", fmt.Sprintf("up=%d queue=%d", size+1, depth))
			} else if depth <= r.cfg.AutoScale.LowWatermark && size > r.cfg.AutoScale.MinWorkers {
				r.pool.Resize(size - 1)
				r.emit("workers.autoscaled", "", fmt.Sprintf("down=%d queue=%d", size-1, depth))
			}
		}
	}
}

func (r *Runtime) isStarted() bool {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.started
}

func (r *Runtime) isCanceled(taskID string) bool {
	t, ok := r.repo.Get(taskID)
	return ok && t.Status == core.StatusCanceled
}

func (r *Runtime) newID() string {
	return fmt.Sprintf("task-%d", time.Now().UTC().UnixNano())
}

func (r *Runtime) newRunID() string {
	return fmt.Sprintf("run-%d-%d", time.Now().UTC().UnixNano(), r.seq.Add(1))
}

func (r *Runtime) emit(name, taskID, message string) {
	if r.events == nil {
		return
	}
	// Registry counters are used as process-local metrics; event details remain
	// intentionally lightweight so handlers can expose them without a logger dependency.
	r.metricMu.Lock()
	if c, ok := r.events.Counters[name]; ok {
		c.Inc()
	} else {
		r.events.Counters[name] = &observability.Counter{}
		r.events.Counters[name].Inc()
	}
	r.metricMu.Unlock()
	_ = observability.Event{Name: name, TaskID: taskID, Message: message}
}


func (r *Runtime) nextScheduledTime(taskID string) (time.Time, bool) {
	for _, item := range r.scheduler.Pending() {
		if item.Task.ID == taskID && item.Task.ScheduledAt != nil {
			return *item.Task.ScheduledAt, true
		}
	}
	return time.Time{}, false
}
