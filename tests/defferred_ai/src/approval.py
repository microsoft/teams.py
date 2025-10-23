"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Callable, Protocol, TypeVar

from microsoft.teams.ai import DeferredResult, Function
from microsoft.teams.ai.function import DeferredFunctionResumer
from microsoft.teams.api import MessageActivityInput
from microsoft.teams.api.activities.message.message import MessageActivity
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class MessageSender(Protocol):
    """Protocol for anything that can send messages."""

    async def send(self, message: str | MessageActivityInput) -> Any:
        """Send a message."""
        ...


class ApprovalParams(BaseModel):
    query: str


def create_approval_function(sender: MessageSender) -> Function[ApprovalParams]:
    """Factory function to create an approval function with captured message sender."""

    async def approval_handler(params: ApprovalParams) -> DeferredResult:
        """Handler that defers execution and sends approval request."""
        # Send the approval request message immediately
        await sender.send(
            "⏳ **Approval Required**\n\n"
            f"**Query:** {params.query}\n\n"
            "Please respond with:\n"
            "• 'yes' or 'approve' to confirm\n"
            "• 'no' or 'deny' to cancel"
        )

        return DeferredResult(
            state={"query": params.query},
        )

    class HumanApprovalResumer(DeferredFunctionResumer[ApprovalParams, Any]):
        """Resumer that handles human approval responses."""

        def can_handle(self, activity: Any) -> bool:
            """Check if this is a text message that looks like an approval response."""
            if isinstance(activity, MessageActivity):
                text = activity.text.lower().strip()
                approval_keywords = ["yes", "no", "approve", "deny", "reject", "confirm", "cancel"]
                return any(keyword in text for keyword in approval_keywords)
            return False

        async def __call__(self, activity: Any, resumable_data: dict[str, Any]) -> str:
            """Process the human approval response."""
            assert isinstance(activity, MessageActivity), "activity must be a MessageActivity"
            user_response = activity.text.lower().strip()
            query = resumable_data.get("query", "unknown query")

            await sender.send("[DEBUG] got approval result from user")
            if any(word in user_response for word in ["yes", "approve", "confirm"]):
                return f"✅ Approved: {query}\nApproval granted by user."
            else:
                return f"❌ Denied: {query}\nApproval denied by user."

    return Function(
        name="get_human_approval",
        description=(
            "You must ALWAYS use this tool to get approvals. Do NOT ask for approvaldirectly without using this tool"
        ),
        parameter_schema=ApprovalParams,
        handler=approval_handler,
        resumer=HumanApprovalResumer(),
    )


def create_approval_wrapped_function[T: BaseModel](
    sender: MessageSender, original_function: Function[T], create_approval_message: Callable[[T], str]
) -> Function[T]:
    """
    Wrap an existing function with approval workflow.

    Args:
        sender: Message sender for approval requests
        original_function: The function to wrap with approval
        create_approval_message: Function to create approval message based on params

    Returns:
        A new function that requires approval before executing the original
    """

    async def wrapped_handler(params: T) -> DeferredResult:
        """Handler that requests approval before executing the original function."""

        # Create approval message using the provided callback
        approval_message = create_approval_message(params)

        print(f"[APPROVAL WRAPPER] Requesting approval for: {original_function.name}")

        # Send the approval request message
        await sender.send(approval_message)

        # Save the call details in state for resume
        return DeferredResult(
            state={
                "params": params.model_dump(),
            },
        )

    class ApprovalWrappedResumer(DeferredFunctionResumer[T, Any]):
        """Resumer that executes the original function after approval."""

        def can_handle(self, activity: Any) -> bool:
            """Check if this is a text message that looks like an approval response."""
            if isinstance(activity, MessageActivity):
                text = activity.text.lower().strip()
                approval_keywords = ["yes", "no", "approve", "deny", "reject", "confirm", "cancel"]
                return any(keyword in text for keyword in approval_keywords)
            return False

        async def __call__(self, activity: Any, resumable_data: dict[str, Any]) -> str:
            """Process the approval response and execute original function if approved."""
            assert isinstance(activity, MessageActivity), "expected activity to be a MessageActivity"
            user_response = activity.text.lower().strip()
            saved_params = resumable_data.get("params", {})

            await sender.send("[DEBUG] Got approval result!")
            if any(word in user_response for word in ["yes", "approve", "confirm"]):
                print("[APPROVAL WRAPPER] Approved, executing original function")

                try:
                    # Recreate the params object and call original function
                    # Cast parameter_schema to the type since we know it should be T for Function[T]
                    schema_type = original_function.parameter_schema
                    if not isinstance(schema_type, type):
                        raise ValueError(f"Expected parameter_schema to be a type, got {type(schema_type)}")

                    params_instance = schema_type(**saved_params)
                    result = original_function.handler(params_instance)

                    # Handle async results
                    from inspect import isawaitable

                    if isawaitable(result):
                        result = await result

                    return f"✅ **Approved and Executed**\n\n{result}"

                except Exception as e:
                    return f"❌ **Approved but Failed**\nError executing {original_function.name}: {str(e)}"
            else:
                return "❌ **Cancelled**\nExecution denied by user."

    # Return wrapped function using original function's name, description, and param_schema
    return Function[T](
        name=original_function.name,
        description=original_function.description,
        parameter_schema=original_function.parameter_schema,
        handler=wrapped_handler,
        resumer=ApprovalWrappedResumer(),
    )
