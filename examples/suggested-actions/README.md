# Example: Suggested Action Submit

A bot that demonstrates the `Action.Submit` suggested action and the `suggestedActions/submit` invoke it produces when clicked.

## Behavior

| Trigger | Behavior |
|---------|----------|
| Any user message | Bot replies with `Approve` / `Reject` suggested-action chips (`type: "Action.Submit"`, each with a structured `value`) |
| User clicks a chip | Platform dispatches a `suggestedActions/submit` invoke; bot reads `activity.value` and echoes it back |

## Notes

- `Action.Submit` chips do not post a chat-visible message on the user's behalf — only the bot receives the click as a typed invoke.
- The chip's `value` is delivered verbatim on `SuggestedActionSubmitInvokeActivity.value`.

## Experimental API

`CardActionType.SUBMIT`, `SuggestedActionSubmitInvokeActivity`, and `on_suggested_action_submit` are marked with `@experimental("ExperimentalTeamsSuggestedAction")` because the underlying platform feature is still rolling out.

This sample opts in by suppressing the warning:

```python
warnings.filterwarnings("ignore", category=ExperimentalWarning, message=".*ExperimentalTeamsSuggestedAction.*")
```

When the API stabilizes, the `@experimental` decorator will be removed and the opt-in can be deleted.

## Run

```bash
cd examples/suggested-actions
uv run python src/main.py
```
