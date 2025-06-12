from typing import Any, Protocol


class Logger(Protocol):
    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Log a message with DEBUG level.

        Args:
            message: The message to log.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        ...

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Log a message with INFO level.

        Args:
            message: The message to log.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        ...

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Log a message with WARNING level.

        Args:
            message: The message to log.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        ...

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Log a message with ERROR level.

        Args:
            message: The message to log.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        ...

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Log a message with CRITICAL level.

        Args:
            message: The message to log.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        ...

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Log a message with ERROR level, including exception info.

        Args:
            message: The message to log.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        ...

    def log(self, level: int, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Log a message with a specified level.

        Args:
            level: The level of the message.
            message: The message to log.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        ...
