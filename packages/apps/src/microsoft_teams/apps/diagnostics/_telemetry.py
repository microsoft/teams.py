"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import importlib.metadata

TEAMS_BOT_APPLICATION_TRACER_NAME = "Microsoft.Teams.Apps"
TEAMS_BOT_APPLICATION_METER_NAME = "Microsoft.Teams.Apps"
TEAMS_BOT_APPLICATION_INSTRUMENTATION_VERSION = importlib.metadata.version("microsoft-teams-apps")


class TeamsBotApplicationTelemetry:
    """OpenTelemetry source names for the Teams app orchestration package."""

    tracer_name = TEAMS_BOT_APPLICATION_TRACER_NAME
    meter_name = TEAMS_BOT_APPLICATION_METER_NAME
    instrumentation_version = TEAMS_BOT_APPLICATION_INSTRUMENTATION_VERSION
