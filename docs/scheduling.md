# Scheduling

Scheduling is handled by internal/scheduler.

## One-shot tasks

A task with a future ScheduledAt is persisted as scheduled and stays outside the ready queue until its timestamp is due.

The scheduler stores nanosecond timestamps internally, so sub-second accuracy is not lost by integer-second truncation.

## Recurring tasks

A recurring task has:

- ScheduledAt: the first occurrence;
- RepeatEvery: a positive duration.

When an occurrence becomes due:

1. the scheduler emits the current task;
2. the recurring item remains registered;
3. the next occurrence is calculated;
4. the runtime gives that occurrence a fresh RunID;
5. the occurrence enters the ready queue.

The logical task ID remains stable.

## Dynamic changes

The runtime supports:

- scheduling a previously created task;
- changing its schedule;
- changing a recurring task into a one-shot schedule by supplying repeat = 0 through the runtime API;
- canceling a schedule.

The scheduler itself owns schedule membership. The repository owns durable lifecycle state.

## Missed occurrences

TaskMesh does not replay every missed interval after downtime. The next occurrence is advanced into the future relative to the current scheduler clock.

This prevents a large backlog of stale recurrence executions after a long process pause.

A future durable cron implementation could add an explicit catch-up policy, but catch-up should be a documented policy rather than an accidental side effect.

## Testing

Scheduler.New accepts a Clock function. Tests can supply a deterministic clock, making Due, reschedule and recurrence logic testable without real-time sleeps.

## Public scheduler operations

- Schedule
- Reschedule
- Cancel
- Due
- Pending
- Len

The scheduler is deliberately unaware of HTTP, workers and persistence.
