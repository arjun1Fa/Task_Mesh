# taskmeshctl

taskmeshctl is intentionally a thin HTTP client.

## Design

The CLI is split into:

- argument parsing;
- command definitions;
- help text;
- request construction;
- HTTP execution;
- response handling.

The CLI should not duplicate runtime business logic. When scheduling or worker behavior changes, the runtime/API should be updated first and the CLI should remain a transport client.

## Typical responsibilities

Argument parsing converts command-line values into typed request values.

Request code adds the TaskMesh HTTP base URL and sends the appropriate method/body.

Command code decides which endpoint to call.

## Extension rule

When adding a new command:

1. define the command in internal/cli/commands.go;
2. add parsing tests;
3. add request tests;
4. keep the endpoint contract documented in docs/api.md;
5. avoid implementing orchestration policy inside the CLI.
