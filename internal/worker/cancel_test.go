package worker

import ("context"; "testing")

func TestCanceledContext(t *testing.T) { ctx,cancel:=context.WithCancel(context.Background()); cancel(); if !Canceled(ctx) { t.Fatal("expected canceled") } }
