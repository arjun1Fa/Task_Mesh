package cli

func Parse(args []string) Args { out:=Args{}; if len(args)>0 { out.Command=args[0] }; if len(args)>1 { out.TaskID=args[1] }; return out }
