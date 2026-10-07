package auth

import ("context"; "testing")

func TestSubjectContext(t *testing.T) { if Subject(WithSubject(context.Background(),"arjun"))!="arjun" { t.Fatal("subject missing") } }
