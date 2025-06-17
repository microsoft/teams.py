from enum import Enum


class MessagingExtensionResultType(str, Enum):
    """
    Enum representing the type of result for a messaging extension.
    """

    RESULT = "result"
    AUTH = "auth"
    CONFIG = "config"
    MESSAGE = "message"
    BOT_MESSAGE_PREVIEW = "botMessagePreview"
    SILENT_AUTH = "silentAuth"
