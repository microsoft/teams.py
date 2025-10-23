"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from typing import Any, Protocol

from microsoft.teams.ai import BaseAIPlugin, DeferredResult, Function, execute_function
from microsoft.teams.api import MessageActivityInput
from microsoft.teams.common.logging.console import ConsoleLogger
from pydantic import BaseModel


class MessageSender(Protocol):
    """Protocol for anything that can send messages."""

    async def send(self, message: str | MessageActivityInput) -> Any:
        """Send a message."""
        ...


class ApprovalPlugin(BaseAIPlugin):
    """
    Plugin that wraps specified functions with approval workflow.

    This plugin intercepts function calls, requests approval from the user,
    and executes the original function only after approval is granted.
    """

    def __init__(self, sender: MessageSender, functions: list[Function[Any]], *, logger: logging.Logger | None = None):
        """
        Initialize the approval plugin.

        Args:
            sender: Message sender for sending approval requests
            fn_names: List of function names to wrap with approval workflow
        """
        super().__init__("approval")
        self.sender = sender
        self.logger: logging.Logger = logger or ConsoleLogger().create_logger("ApprovalPlugin")
        self._original_functions: dict[str, Function[BaseModel]] = {f.name: f for f in functions}

    async def on_resume(self, function_name: str, activity: Any, state: dict[str, Any]) -> str | None:
        """
        Handle approval responses when resuming deferred functions.

        Args:
            function_name: Name of the function that was deferred
            activity: Activity data to use for resolving
            state: The state that was saved when function was deferred

        Returns:
            Result string if this plugin handled the approval, None otherwise
        """
        # Only handle functions we're wrapping
        if function_name not in self._original_functions:
            return None

        # Check if this activity has text (duck typing for MessageActivity)
        if not hasattr(activity, "text") or not isinstance(activity.text, str):
            return None

        text = activity.text.lower().strip()
        approval_keywords = ["yes", "no", "approve", "deny", "reject", "confirm", "cancel"]
        if not any(keyword in text for keyword in approval_keywords):
            return None  # Not an approval response yet

        # Handle approval/denial
        if any(word in text for word in ["yes", "approve", "confirm"]):
            return await self._execute_wrapped_function(function_name, state)
        else:
            return f"Denied: Execution of {function_name} was cancelled by user."

    async def on_build_functions(self, functions: list[Function[BaseModel]]) -> list[Function[BaseModel]] | None:
        """
        Wrap specified functions with approval workflow.

        Args:
            functions: Current list of available functions

        Returns:
            Updated function list with wrapped functions
        """
        # Wrap each specified function
        wrapped_functions: list[Function[BaseModel]] = []
        for func in functions:
            if func.name in self._original_functions:
                if func.resumer is not None:
                    self.logger.warning(
                        f"{func.name} seems to be a resumable function. ApprovalPlugin only works"
                        "for functions that are not resumable themselves."
                    )
                    continue
                wrapped_func = self._create_wrapped_function(func)
                wrapped_functions.append(wrapped_func)
            else:
                wrapped_functions.append(func)

        return wrapped_functions

    def _create_wrapped_function(self, original_func: Function[BaseModel]) -> Function[BaseModel]:
        """
        Create a wrapped version of a function that requires approval.

        Args:
            original_func: The original function to wrap

        Returns:
            Wrapped function that defers for approval before execution
        """
        # Store original function for later execution

        self.logger.debug(f"Wrapping {original_func.name} with ApprovalPlugin Function")

        async def wrapped_handler(params: BaseModel) -> DeferredResult:
            """Handler that requests approval before executing original function."""
            # Send approval request
            await self.sender.send(
                f"Approval Required\n\n"
                f"Function: {original_func.name}\n"
                f"Parameters: {params.model_dump()}\n\n"
                "Please respond with:\n"
                "- 'yes' or 'approve' to confirm\n"
                "- 'no' or 'deny' to cancel"
            )

            # Save params for later execution
            return DeferredResult(
                state={
                    "params": params.model_dump(),
                    "original_function_name": original_func.name,
                },
            )

        return Function(
            name=original_func.name,
            description=original_func.description,
            parameter_schema=original_func.parameter_schema,
            handler=wrapped_handler,
            resumer=None,  # Plugin handles resuming via on_resume hook
        )

    async def _execute_wrapped_function(self, function_name: str, state: dict[str, Any]) -> str:
        """
        Execute the original wrapped function after approval.

        Args:
            function_name: Name of the function to execute
            state: State containing saved parameters

        Returns:
            Result from executing the original function
        """
        original_func = self._original_functions.get(function_name)
        if not original_func:
            raise ValueError(f"Could not re-run original function {function_name} because it no longer exists")
        try:
            # Recreate params from saved state
            saved_params = state.get("params", {})
            self.logger.info(f"Running original function {function_name} after approval")
            result = await execute_function(original_func, saved_params)
            if isinstance(result, DeferredResult):
                raise ValueError(
                    "Functions that use ApprovalPlugin cannot be deferrable!"
                    f"And {original_func.name} just returned a DeferredResult"
                )
            return result
        except Exception as e:
            return f"Approved but Failed\nError executing {function_name}: {str(e)}"
