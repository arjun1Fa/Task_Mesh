package worker

import "context"

func (p *Pool) RunOne(ctx context.Context, executor Executor) Result {
  task,ok:=p.queue.Dequeue()
  if !ok { return Result{} }
  return Runtime{}.Dispatch(ctx,executor,task)
}
