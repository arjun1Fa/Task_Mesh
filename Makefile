test:
	go test ./...

fmt:
	gofmt -w cmd internal tests

run:
	go run ./cmd/taskmesh
