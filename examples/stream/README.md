# Stream Test App

A test application that demonstrates streaming functionality.

- Send any message for the normal single-stream demo with suggested actions.
- Send `simple-card` to send a minimal Adaptive Card outside the streaming flow.
- Send `multi-stream` to test finalizing the current stream with `close(reset=True)`, sending an Adaptive Card, and then reusing `ctx.stream` for another streamed response.

## Running

```bash
python src/main.py
```
