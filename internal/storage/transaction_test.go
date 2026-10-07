package storage

import "testing"

func TestTransactionLifecycle(t *testing.T) { var tx Transaction; tx.Begin(); if !tx.Active { t.Fatal("transaction not active") }; tx.Commit(); if tx.Active { t.Fatal("transaction still active") } }
