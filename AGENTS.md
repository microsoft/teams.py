# Repository Agent Guidance

- Activity inputs are pydantic models. Access known fields directly (for example, `activity.type`) instead of using defensive `getattr` calls.
