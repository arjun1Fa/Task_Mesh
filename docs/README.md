# TaskMesh documentation

This directory is the executable specification of the project. It answers both "how do I use TaskMesh?" and "why is this code here?"

## Reading order

### Architecture and code

- [architecture.md](architecture.md) — component boundaries, ownership and lifecycle.
- [runtime.md](runtime.md) — the orchestration engine, state transitions, retry, cancellation and recovery.
- [codebase.md](codebase.md) — file-by-file guide to the repository.
- [development.md](development.md) — development and contribution workflow.

### Features

- [api.md](api.md) — HTTP routes, request formats and examples.
- [scheduling.md](scheduling.md) — delayed, recurring and dynamic scheduling.
- [workers.md](workers.md) — worker registration and live resizing.
- [retries.md](retries.md) — retry and backoff behavior.
- [idempotency.md](idempotency.md) — duplicate submission semantics.
- [dead-letter-queue.md](dead-letter-queue.md) — failure isolation and recovery.
- [cancellation.md](cancellation.md) — cancellation semantics.
- [observability.md](observability.md) — metrics and event concepts.
- [storage.md](storage.md) — repository contract and durability.
- [configuration.md](configuration.md) — environment configuration.
- [security.md](security.md) — transport and authentication considerations.
- [cli.md](cli.md) — command-line client behavior.

## Mental model

A task is a durable description of work. A schedule decides when it may enter the ready queue. A queue decides which ready task is selected next. A worker decides how many tasks can execute concurrently. The registry decides which handler executes a task name. Retry and dead-letter logic decide what happens after failure. The repository records the latest durable lifecycle state.

The runtime owns the transitions between those components; individual packages should stay small, testable and transport-independent.
