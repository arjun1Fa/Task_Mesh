package idempotency

import "sync"

type Store struct {
	mu   sync.RWMutex
	keys map[Key]string
}

func NewStore() *Store { return &Store{keys: make(map[Key]string)} }

func (s *Store) Seen(k Key) (string, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	v, ok := s.keys[k]
	return v, ok
}

// Reserve atomically records a key unless another task already owns it.
// The returned existing ID is empty for a successful reservation.
func (s *Store) Reserve(k Key, taskID string) (existing string, ok bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if v, exists := s.keys[k]; exists {
		return v, true
	}
	s.keys[k] = taskID
	return "", false
}

func (s *Store) Record(k Key, taskID string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.keys[k] = taskID
}

func (s *Store) Forget(k Key) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.keys, k)
}
