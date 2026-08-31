# Stream Test App

A test application that demonstrates streaming functionality.

- Send any message for the normal single-stream demo with suggested actions.
- Send `simple-card` to send a minimal Adaptive Card outside the streaming flow.
- Send `extended-markdown` to stream a message where every chunk sets `text_format="extendedmarkdown"` — task-list checkboxes and strikethrough render as they stream, which plain markdown can't do. The leading informative update uses the new `stream.update(text, "markdown")` overload.
- Send `multi-stream` to test emitting an Adaptive Card as part of the first stream final message, finalizing with `close()`, and then reusing `ctx.stream` for another streamed response.

## Running

```bash
python src/main.py
```
