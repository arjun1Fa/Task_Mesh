package observability

type Sink interface { Emit(Event) }
