package storage

import "testing"

func TestMemoryRepositoryExists(t *testing.T) { r:=NewMemoryRepository(); if r==nil { t.Fatal("repository missing") } }
