package storage

import "errors"

var (
	ErrNotFound      = errors.New("task not found")
	ErrAlreadyExists = errors.New("task already exists")
)
