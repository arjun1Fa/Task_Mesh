package auth

type Store struct { tokens map[string]Token }

func NewStore() *Store { return &Store{tokens:map[string]Token{}} }
func (s *Store) Add(t Token) { s.tokens[t.Value]=t }
func (s *Store) Get(value string) (Token,bool) { t,ok:=s.tokens[value]; return t,ok }
