package cli

import "testing"

func TestParse(t *testing.T) { a:=Parse([]string{"get","abc"}); if a.Command!="get"||a.TaskID!="abc" { t.Fatal("bad arguments") } }
