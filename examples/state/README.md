# State

Demonstrates the per-turn state layer: enabling it with `App(state=True)` and
reading/writing the `conversation` and `user` scopes through `ctx.state`.

State is loaded before each turn, saved automatically after it, and then sealed
(post-turn access raises `TurnStateSealedError`). With no storage configured the
app uses in-memory `LocalStorage`; pass `App(state=StateOptions(storage=...))`
for a durable backing store.

## Run

```bash
uv run --directory examples/state src/main.py
```
