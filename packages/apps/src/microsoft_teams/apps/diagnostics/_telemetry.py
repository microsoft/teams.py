"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

TEAMS_BOT_APPLICATION_TRACER_NAME = "Microsoft.Teams.Apps"
TEAMS_BOT_APPLICATION_METER_NAME = "Microsoft.Teams.Apps"


class TeamsBotApplicationTelemetry:
    """OpenTelemetry source names for the Teams app orchestration package."""

    tracer_name = TEAMS_BOT_APPLICATION_TRACER_NAME
    meter_name = TEAMS_BOT_APPLICATION_METER_NAME
