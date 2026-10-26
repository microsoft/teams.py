# Plan Test App

A test application that demonstrates Plan lifecycles with self-contained message handlers.
Each step includes a description that changes as it progresses through the demo.

- Send `complete` to demonstrate an active lookup becoming blocked and then completed with a source, while a proposed answer step becomes active and then completed. Finish with a normal answer message.
- Send `complete-stream` to demonstrate the same steps and finish with a streamed answer. The handler emits completion metadata last, then calls `close()`; only the final message carries the complete plan.
- Send `stop` to start a Plan and then stop it.
- Send `error` to start a Plan, mark its lookup step as `error`, and then end the Plan with an error.
- Send `proactive` to schedule a Plan that starts five seconds after the handler returns, updates its report step, and completes with a normal answer. No second message is needed.

The proactive demo keeps a prompt-bound `Plan` for the background task, rather than using the activity context after the handler returns.

## Running

```bash
python src/main.py
```
