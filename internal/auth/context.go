package auth

import "context"

type contextKey string

const subjectKey contextKey = "taskmesh.subject"

func WithSubject(ctx context.Context, subject string) context.Context { return context.WithValue(ctx,subjectKey,subject) }
func Subject(ctx context.Context) string { v,_:=ctx.Value(subjectKey).(string); return v }
