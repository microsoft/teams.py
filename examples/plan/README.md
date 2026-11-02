# Plan Test App

> **Preview:** `Plan`, `PlanOptions`, `ctx.plan()`, and the Plan models and type aliases may change.
> The `Plan` constructor and context factory emit `ExperimentalWarning` with diagnostic
> `ExperimentalTeamsPlan`.

A test application that demonstrates Plan lifecycles with self-contained message handlers.
Each step includes a description that changes as it progresses through the demo.

- Send `complete` to demonstrate an active lookup becoming blocked and then completed with a source, while a proposed answer step becomes active and then completed. Finish with a normal answer message.
- Send `complete-stream` to demonstrate the same steps and finish with a streamed answer using `plan.completion()`; only the final message carries the complete plan.
- Send `stop` to start a Plan and then stop it.
- Send `error` to start a Plan, mark its lookup step as `error`, and then end the Plan with an error.
- Send `proactive` to manage a Plan proactively.

`PlanOptions` requires `conversation_id`, `reply_to_id`, and `api_client`, but
`Plan.model_dump()` serializes only the two IDs. Store those IDs and supply the configured API client when rebuilding `PlanOptions`.

The delays stand in for longer-running work.

For streaming, emit the completion message last on a stream targeting the same conversation, then close it:

```python
ctx.stream.emit(plan.completion())
await ctx.stream.close()
```

`completion()` builds a fresh message bound to the Plan's prompt; it does not send, emit events, or close the stream.
Use the message's fluent methods to add final metadata. For a non-streamed answer, `await plan.complete(message)` still sends directly.

## Running

```bash
python src/main.py
```
