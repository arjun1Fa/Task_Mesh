package worker

import (
	"context"
	"sync"
	"sync/atomic"
	"taskmesh/internal/core"
	"taskmesh/internal/queue"
	"time"
)

// Pool is a dynamically resizable worker pool.
//
// Resize can be called while the pool is running. Reducing the size cancels
// workers gracefully; increasing it starts additional workers immediately.
type Pool struct {
	queue    queue.TaskQueue
	executor Executor

	mu      sync.Mutex
	workers map[int]context.CancelFunc
	rootCtx context.Context
	nextID  int
	running bool
	target  atomic.Int64
	wg      sync.WaitGroup
}

func NewPool(q queue.TaskQueue, e Executor, workers int) *Pool {
	if workers < 1 {
		workers = 1
	}
	p := &Pool{queue: q, executor: e, workers: make(map[int]context.CancelFunc)}
	p.target.Store(int64(workers))
	return p
}

// Run starts the initial worker set and blocks until the supplied context is
// canceled or Stop is called. Calling Run more than once is unsupported.
func (p *Pool) Run(ctx context.Context) {
	p.mu.Lock()
	if p.running {
		p.mu.Unlock()
		return
	}
	p.running = true
	p.rootCtx = ctx
	target := int(p.target.Load())
	for i := 0; i < target; i++ {
		p.startWorkerLocked()
	}
	p.mu.Unlock()

	<-ctx.Done()
	p.stopAll()
	p.wg.Wait()
}

func (p *Pool) Resize(n int) {
	if n < 1 {
		n = 1
	}
	p.target.Store(int64(n))

	p.mu.Lock()
	defer p.mu.Unlock()
	if !p.running {
		return
	}
	for len(p.workers) < n {
		p.startWorkerLocked()
	}
	for len(p.workers) > n {
		for id, cancel := range p.workers {
			cancel()
			delete(p.workers, id)
			break
		}
	}
}

func (p *Pool) Size() int { return int(p.target.Load()) }

func (p *Pool) startWorkerLocked() {
	id := p.nextID
	p.nextID++
	ctx, cancel := context.WithCancel(p.rootCtx)
	p.workers[id] = cancel
	p.wg.Add(1)
	go p.loop(ctx, id)
}

func (p *Pool) loop(ctx context.Context, id int) {
	defer p.wg.Done()
	defer func() {
		p.mu.Lock()
		delete(p.workers, id)
		p.mu.Unlock()
	}()

	for {
		var (
			t  core.Task
			ok bool
		)
		if bq, supported := p.queue.(queue.BlockingTaskQueue); supported {
			t, ok = bq.DequeueContext(ctx)
		} else {
			t, ok = p.queue.Dequeue()
			if !ok {
				select {
				case <-ctx.Done():
					return
				case <-time.After(10 * time.Millisecond):
				}
				continue
			}
		}
		if !ok {
			return
		}
		if ctx.Err() != nil {
			return
		}
		_ = p.executor.Execute(t)
	}
}

func (p *Pool) stopAll() {
	p.mu.Lock()
	defer p.mu.Unlock()
	for id, cancel := range p.workers {
		cancel()
		delete(p.workers, id)
	}
	p.running = false
}
