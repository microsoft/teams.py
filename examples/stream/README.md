# Stream Test App

A test application that demonstrates streaming functionality.

- Send any message for the normal single-stream demo with suggested actions.
- Send `multi-stream` to test finalizing the current stream with `close(reset=True)`, sending a normal message, and then reusing `ctx.stream` for another streamed response.

## Running

```bash
python src/main.py
```
