package storage

type Transaction struct { Active bool }

func (t *Transaction) Begin() { t.Active=true }
func (t *Transaction) Rollback() { t.Active=false }
func (t *Transaction) Commit() { t.Active=false }
