# Storage

TaskMesh starts with an in-memory repository for development and defines a SQLite-backed adapter for durable task state. The repository contract keeps the API independent of the storage engine.
