# Retries

Retry primitives live in internal/retry. Runtime execution lives in internal/runtime.

## Policy

Policy contains:

- MaxAttempts
- BaseDelay

Attempts is normalized to at least one.

## Backoff

Delay is calculated by the retry package. Runtime waits between attempts using a timer tied to the execution context, so cancellation or timeout can interrupt the wait.

## Lifecycle

A failed attempt causes the runtime to:

1. retain the last error;
2. persist retrying when another attempt is available;
3. emit a retry metric;
4. wait for the calculated delay;
5. try again.

When attempts are exhausted, the logical task moves to dead_letter and a DLQ entry is stored.

## Timeout interaction

Task Timeout bounds the execution context used by the runtime. A timeout can stop future retry attempts as well as interrupt a retry wait.

The current Executor interface does not accept that context directly. Context-aware handler execution is therefore a deliberate future interface improvement.

## Failure semantics

All executor errors are treated as retry candidates by the current runtime. A future version can classify errors as permanent or transient before applying policy.
