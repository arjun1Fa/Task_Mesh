# Development

## Local checks

Run the complete test suite:

    make test

Format source:

    make fmt

Run static analysis:

    go vet ./...

Run the service:

    make run

The CI pipeline checks formatting, vet and go test.

## Change workflow

A good change should follow the package boundary:

1. update or add a domain type if the behavior changes task semantics;
2. add the smallest package implementation;
3. add unit tests next to that implementation;
4. wire orchestration in internal/runtime;
5. expose transport behavior in internal/api;
6. update the matching documentation page;
7. update architecture/codebase documentation when the dependency graph changes.

## Testing philosophy

Use deterministic clocks for scheduler tests.

Use MemoryRepository for package-level runtime tests.

Use short context deadlines instead of long sleeps when testing cancellation.

Use integration tests for cross-package wiring.

## Pull requests

A feature PR should explain:

- why the feature exists;
- which state transitions it adds;
- how failure/cancellation behave;
- what tests cover the new behavior;
- what production limitations remain.

Keep commits meaningful. Do not generate history solely to inflate commit counts.
