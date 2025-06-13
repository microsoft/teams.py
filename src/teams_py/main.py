"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft.teams.common.logging import ConsoleLogger

logger = ConsoleLogger().create_logger(__name__)


def main():
    logger.info("This is a log message from the main function.")


if __name__ == "__main__":
    main()
